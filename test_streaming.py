"""Test script to verify Ollama streaming works correctly."""

import requests
import json
import time

def test_streaming():
    """Test streaming with chunk_size=1 to verify real-time response."""
    url = "http://localhost:11434/api/generate"

    payload = {
        "model": "gemma3:27b",
        "prompt": "Say 'Hello, streaming is working!' in a short sentence.",
        "stream": True
    }

    print("Testing Ollama streaming...")
    print(f"URL: {url}")
    print(f"Model: {payload['model']}")
    print("-" * 50)

    try:
        response = requests.post(url, json=payload, stream=True)
        response.raise_for_status()

        print("Connected! Starting to receive chunks...\n")

        chunk_count = 0
        start_time = time.time()
        first_chunk_time = None

        for line in response.iter_lines(chunk_size=1):
            if line:
                data = line.decode('utf-8')
                if data.startswith('{'):
                    chunk = json.loads(data)
                    if 'response' in chunk:
                        if first_chunk_time is None:
                            first_chunk_time = time.time()
                            time_to_first = (first_chunk_time - start_time) * 1000
                            print(f"[DEBUG] Time to first chunk: {time_to_first:.0f}ms")

                        chunk_text = chunk['response']
                        chunk_count += 1
                        print(chunk_text, end='', flush=True)

                        if chunk.get('done'):
                            total_time = (time.time() - start_time) * 1000
                            print(f"\n\n{'=' * 50}")
                            print(f"Total chunks received: {chunk_count}")
                            print(f"Total time: {total_time:.0f}ms")
                            print(f"Streaming appears to be working!")
                            return True

        print(f"\n{'=' * 50}")
        print("No chunks received")
        return False

    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to Ollama.")
        print("Make sure Ollama is running with: ollama serve")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_streaming()
    if success:
        print("\nStreaming test PASSED!")
    else:
        print("\nStreaming test FAILED!")
