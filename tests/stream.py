import httpx

def listen_to_stream(url):
    with httpx.Client(timeout=None) as client:
        with client.stream("GET", url) as response:
            # Read the streaming response line by line
            for line in response.iter_lines():
                if line:
                    # line is already a string, no decoding needed
                    if line.startswith("data: "):
                        data = line[len("data: "):]
                        print("Received event data:", data)

if __name__ == "__main__":
    stream_url = "http://127.0.0.1:8000/stream"
    print(f"Connecting to {stream_url} and listening for events...")
    listen_to_stream(stream_url)
