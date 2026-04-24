"""
Utility for streaming tokens from DeepSeek-R1 and other reasoning models.
DeepSeek-R1 outputs <think>...</think> before the real answer.
We strip this so users only see the clean explanation.
"""

def stream_clean(groq_stream):
    """
    Generator that strips <think>...</think> blocks from streamed output.
    Works token by token so it handles partial tags across chunks.
    """
    buffer = ""
    in_think = False

    for chunk in groq_stream:
        token = chunk.choices[0].delta.content
        if not token:
            continue

        buffer += token

        # Process buffer
        while buffer:
            if in_think:
                # Look for closing tag
                end = buffer.find("</think>")
                if end != -1:
                    # Found end of think block
                    buffer = buffer[end + len("</think>"):]
                    in_think = False
                else:
                    # Still inside think block, discard buffer but keep
                    # last few chars in case closing tag is split across chunks
                    if len(buffer) > 10:
                        buffer = buffer[-9:]  # keep enough to detect </think>
                    break
            else:
                # Look for opening tag
                start = buffer.find("<think>")
                if start != -1:
                    # Yield everything before the think tag
                    clean = buffer[:start]
                    if clean:
                        yield clean
                    buffer = buffer[start + len("<think>"):]
                    in_think = True
                else:
                    # Check if buffer might contain partial opening tag
                    partial = False
                    for i in range(1, len("<think>")):
                        if buffer.endswith("<think>"[:i]):
                            # Yield safe part, keep potential partial tag
                            safe = buffer[:-i]
                            if safe:
                                yield safe
                            buffer = buffer[-i:]
                            partial = True
                            break
                    if not partial:
                        yield buffer
                        buffer = ""
                    break

    # Yield any remaining buffer content
    if buffer and not in_think:
        yield buffer
