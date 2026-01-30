"""
CLI utilities for audit replay operations
"""

import asyncio
import json
import sys
from typing import Dict, Any, List
from datetime import datetime, timezone

import click
from tabulate import tabulate

from .replay_engine import ReplayEngine, ReplayReport, ReplayResult
from .canonical_utils import canonical_json, stable_hash


@click.group()
def replay():
    """Audit replay CLI utilities"""
    pass


@replay.command()
@click.argument('correlation_id')
@click.option('--audit-store', default='audit_store.json', help='Audit store file path')
@click.option('--output', '-o', help='Output report file path')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def run(correlation_id: str, audit_store: str, output: str, verbose: bool):
    """Run replay for a correlation ID"""
    
    # Load audit store
    try:
        with open(audit_store, 'r') as f:
            audit_data = json.load(f)
    except FileNotFoundError:
        click.echo(f"Error: Audit store file not found: {audit_store}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON in audit store: {e}")
        sys.exit(1)
    
    # Convert to AuditRecordV1 objects (simplified for CLI)
    audit_records = _convert_to_audit_records(audit_data.get(correlation_id, []))
    
    # Initialize replay engine
    engine = ReplayEngine({correlation_id: audit_records})
    
    # Run replay
    click.echo(f"Running replay for correlation_id: {correlation_id}")
    report = engine.replay_correlation(correlation_id)
    
    # Display results
    _display_report(report, verbose)
    
    # Save report if requested
    if output:
        _save_report(report, output)
        click.echo(f"Report saved to: {output}")


@replay.command()
@click.argument('audit_file')
@click.option('--output', '-o', help='Output envelope file path')
def envelope(audit_file: str, output: str):
    """Convert audit records to canonical envelopes"""
    
    try:
        with open(audit_file, 'r') as f:
            audit_data = json.load(f)
    except FileNotFoundError:
        click.echo(f"Error: Audit file not found: {audit_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON in audit file: {e}")
        sys.exit(1)
    
    envelopes = []
    for correlation_id, records in audit_data.items():
        audit_records = _convert_to_audit_records(records)
        for i, record in enumerate(audit_records):
            try:
                from .event_envelope import AuditEventEnvelope
                envelope = AuditEventEnvelope.from_audit_record(record, sequence_number=i)
                envelopes.append({
                    'correlation_id': correlation_id,
                    'envelope': envelope.to_dict()
                })
            except Exception as e:
                click.echo(f"Warning: Failed to create envelope for record {record.event_id}: {e}")
    
    if output:
        with open(output, 'w') as f:
            json.dump(envelopes, f, indent=2)
        click.echo(f"Envelopes saved to: {output}")
    else:
        click.echo(json.dumps(envelopes, indent=2))


@replay.command()
@click.argument('data_file')
def hash_data(data_file: str):
    """Compute canonical hash of data file"""
    
    try:
        with open(data_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        click.echo(f"Error: Data file not found: {data_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON in data file: {e}")
        sys.exit(1)
    
    canonical = canonical_json(data)
    hash_value = stable_hash(canonical)
    
    click.echo(f"Canonical hash: {hash_value}")
    click.echo(f"Canonical representation length: {len(canonical)} characters")


def _convert_to_audit_records(records_data: List[Dict[str, Any]]) -> List['AuditRecordV1']:
    """Convert dict data to AuditRecordV1 objects (simplified)"""
    records = []
    
    for record_data in records_data:
        try:
            # Create a simplified AuditRecordV1-like object
            class SimpleAuditRecord:
                def __init__(self, data):
                    self.event_id = data.get('event_id', '')
                    self.timestamp = datetime.fromisoformat(data.get('timestamp', '').replace('Z', '+00:00'))
                    self.event_kind = data.get('event_kind', '')
                    self.actor = data.get('actor', '')
                    self.correlation_id = data.get('correlation_id', '')
                    self.cell_id = data.get('cell_id', '')
                    self.tenant_id = data.get('tenant_id', '')
                    self.trace_id = data.get('trace_id', '')
                    self.payload_ref = data.get('payload_ref', {})
            
            records.append(SimpleAuditRecord(record_data))
            
        except Exception as e:
            click.echo(f"Warning: Failed to convert audit record: {e}")
    
    return records


def _display_report(report: ReplayReport, verbose: bool):
    """Display replay report in formatted table"""
    
    # Summary table
    summary_data = [
        ['Correlation ID', report.correlation_id],
        ['Result', report.result.value.upper()],
        ['Total Events', report.total_events],
        ['Processed Events', report.processed_events],
        ['Failed Events', report.failed_events],
        ['Intent Hash Verified', '✅' if report.intent_hash_verified else '❌'],
        ['Safety Gate Verified', '✅' if report.safety_gate_verified else '❌'],
        ['Audit Integrity Verified', '✅' if report.audit_integrity_verified else '❌']
    ]
    
    click.echo("\n" + "="*60)
    click.echo("REPLAY REPORT SUMMARY")
    click.echo("="*60)
    click.echo(tabulate(summary_data, headers=['Metric', 'Value'], tablefmt='grid'))
    
    # Failures
    if report.failures:
        click.echo("\n" + "FAILURES:")
        for i, failure in enumerate(report.failures, 1):
            click.echo(f"  {i}. {failure}")
    
    # Warnings
    if report.warnings:
        click.echo("\n" + "WARNINGS:")
        for i, warning in enumerate(report.warnings, 1):
            click.echo(f"  {i}. {warning}")
    
    # Verbose details
    if verbose:
        click.echo("\n" + "VERBOSE DETAILS:")
        click.echo("-" * 40)
        
        if report.reconstructed_intents:
            click.echo(f"\nReconstructed Intents ({len(report.reconstructed_intents)}):")
            for intent_id, intent in report.reconstructed_intents.items():
                click.echo(f"  - {intent_id}: {intent.action_class}")
        
        if report.safety_gate_verdicts:
            click.echo(f"\nSafety Gate Verdicts ({len(report.safety_gate_verdicts)}):")
            for event_id, verdict in report.safety_gate_verdicts.items():
                click.echo(f"  - {event_id}: {verdict}")


def _save_report(report: ReplayReport, output_path: str):
    """Save replay report to file"""
    
    report_data = {
        'correlation_id': report.correlation_id,
        'replay_timestamp': report.replay_timestamp.isoformat(),
        'result': report.result.value,
        'total_events': report.total_events,
        'processed_events': report.processed_events,
        'failed_events': report.failed_events,
        'intent_hash_verified': report.intent_hash_verified,
        'safety_gate_verified': report.safety_gate_verified,
        'audit_integrity_verified': report.audit_integrity_verified,
        'reconstructed_intents': {
            k: v.model_dump() if hasattr(v, 'model_dump') else str(v)
            for k, v in report.reconstructed_intents.items()
        },
        'safety_gate_verdicts': report.safety_gate_verdicts,
        'failures': report.failures,
        'warnings': report.warnings
    }
    
    with open(output_path, 'w') as f:
        json.dump(report_data, f, indent=2)


if __name__ == '__main__':
    replay()
