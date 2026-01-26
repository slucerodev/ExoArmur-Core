#!/usr/bin/env python3
"""
Export audit stream for cold replay verification
"""

import asyncio
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))
sys.path.append(str(Path(__file__).parent.parent))

from nats_client import ExoArmurNATSClient, NATSConfig


async def export_audit_stream(nats_url: str, stream_name: str, output_file: str):
    """Export all messages from audit stream to JSONL format"""
    print(f"Exporting audit stream {stream_name} to {output_file}")
    
    # Connect to NATS
    config = NATSConfig()
    config.url = nats_url
    nats_client = ExoArmurNATSClient(config)
    
    try:
        await nats_client.connect()
        
        # Get stream info
        stream_info = await nats_client.js.stream_info(stream_name)
        print(f"Stream info: {stream_info.state.messages} messages, {stream_info.state.bytes} bytes")
        
        # Export messages using direct stream access
        exported_messages = []
        
        try:
            # Get stream info first
            stream_info = await nats_client.js.stream_info(stream_name)
            print(f"Stream has {stream_info.state.messages} messages")
            
            # Use direct message retrieval
            # Create a consumer to read messages
            consumer = await nats_client.js.add_consumer(
                stream_name,
                durable_name="export_consumer",
                deliver_policy="all"
            )
            
            # Fetch messages in batches
            total_fetched = 0
            max_fetch = stream_info.state.messages
            
            while total_fetched < max_fetch:
                try:
                    # Fetch a small batch
                    msgs = await consumer.fetch(min(5, max_fetch - total_fetched), timeout=1)
                    
                    if not msgs:
                        break
                    
                    for msg in msgs:
                        try:
                            # Parse message data
                            data = json.loads(msg.data.decode())
                            
                            # Add metadata
                            export_entry = {
                                "sequence": getattr(msg, 'sequence', total_fetched),
                                "timestamp": getattr(msg, 'timestamp', 0),
                                "subject": getattr(msg, 'subject', 'exoarmur.audit.append.v1'),
                                "data": data,
                                "headers": dict(msg.headers) if msg.headers else {}
                            }
                            
                            exported_messages.append(export_entry)
                            total_fetched += 1
                            
                        except Exception as e:
                            print(f"Failed to parse message {total_fetched}: {e}")
                            continue
                            
                except Exception as e:
                    print(f"Fetch batch failed: {e}")
                    break
            
            # Clean up consumer
            try:
                await consumer.delete()
            except:
                pass
                    
        except Exception as e:
            print(f"Export failed: {e}")
        
        print(f"Successfully exported {len(exported_messages)} messages")
        
        # Write export file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            for entry in exported_messages:
                f.write(json.dumps(entry) + '\n')
        
        print(f"Exported {len(exported_messages)} messages to {output_path}")
        
        # Write export metadata
        metadata = {
            "exported_at_utc": datetime.now(timezone.utc).isoformat(),
            "stream_name": stream_name,
            "nats_url": nats_url,
            "total_messages": len(exported_messages),
            "stream_messages": stream_info.state.messages,
            "stream_bytes": stream_info.state.bytes,
            "first_seq": stream_info.state.first_seq,
            "last_seq": stream_info.state.last_seq
        }
        
        metadata_file = output_path.with_suffix('.metadata.json')
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return len(exported_messages)
        
    except Exception as e:
        print(f"Export failed: {e}")
        return 0
    
    finally:
        await nats_client.disconnect()


def main():
    parser = argparse.ArgumentParser(description='Export audit stream for replay')
    parser.add_argument('--nats', default='nats://127.0.0.1:4222', help='NATS server URL')
    parser.add_argument('--stream', default='EXOARMUR_AUDIT_V1', help='Stream name')
    parser.add_argument('--out', required=True, help='Output file (JSONL format)')
    
    args = parser.parse_args()
    
    count = asyncio.run(export_audit_stream(args.nats, args.stream, args.out))
    sys.exit(0 if count > 0 else 1)


if __name__ == "__main__":
    main()
