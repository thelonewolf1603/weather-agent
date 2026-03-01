import asyncio
import ollama
import subprocess
import threading
import queue
from mcp import ClientSession
from mcp.client.sse import sse_client

# --- SPEECH QUEUE SYSTEM ---
speech_queue = queue.Queue()

def speech_worker():
    """Worker thread that processes the speech queue one by one."""
    while True:
        text = speech_queue.get()
        if text is None: break
        # Clean text for the 'say' command
        clean_text = text.replace('"', '').replace("'", "").replace('*', '')
        # subprocess.run waits for the speech to finish before moving to the next
        subprocess.run(["say", clean_text])
        speech_queue.task_done()

# Start the speech thread once
threading.Thread(target=speech_worker, daemon=True).start()

def speak(text):
    """Adds text to the speech queue. No more skipping!"""
    if text and len(text.strip()) > 0:
        speech_queue.put(text)

async def main():
    async with sse_client("http://localhost:8000/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            mcp_tools = await session.list_tools()
            ollama_tools = [{
                'type': 'function',
                'function': {
                    'name': t.name,
                    'description': t.description,
                    'parameters': t.inputSchema,
                }
            } for t in mcp_tools.tools]

            print("\n--- Weather Reporter Active (No-Skip Voice) ---")

            messages = [
                {
                    'role': 'system', 
                    'content': (
                        "You are a factual Weather Reporter. "
                        "1. Use get_weather for location queries. "
                        "2. Report numeric temperature and description exactly. "
                        "3. Start your response directly with the info in human readable sentences. "
                        "4. Keep it to 1-2 sentences."
                        "5. do not print json"
                        "6. if you cannnot determine the city, ask the user to provide a city"
                    )
                }
            ]

            while True:
                user_input = input("\nYou: ")
                if user_input.lower() in ["exit", "quit"]:
                    break
                
                messages.append({'role': 'user', 'content': user_input})

                res = ollama.chat(model='llama3.2:latest', messages=messages, tools=ollama_tools)

                if res.message.tool_calls:
                    for tool_call in res.message.tool_calls:
                        args = tool_call.function.arguments
                        args['units'] = 'metric'
                        
                        result = await session.call_tool(tool_call.function.name, arguments=args)
                        
                        messages.append(res.message)
                        messages.append({'role': 'tool', 'content': f"DATA: {result.content[0].text}"})

                    final_res = ollama.chat(model='llama3.2:latest', messages=messages)
                    response_text = final_res.message.content
                else:
                    response_text = res.message.content

                if response_text:
                    print(f"Agent: {response_text}")
                    speak(response_text)
                    messages.append({'role': 'assistant', 'content': response_text})

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nAgent offline.")