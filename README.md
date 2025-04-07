# Python Multimodal Voice Agent

<p>
  • <a href="https://docs.livekit.io/agents/overview/">LiveKit Agents Docs</a>
  
  •<a href = "https://github.com/livekit/agents"> LiveKit Agent Overview </a>
  
</p>


PLAIful Movement Interface Multimodal Agent [Agents Framework](https://github.com/livekit/agents).

## Dev Setup

Clone the repository and install dependencies to a virtual environment:

```console
cd multimodal-agent-python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Set up the environment by copying `.env.example` to `.env.local` and filling in the required values:

- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `OPENAI_API_KEY`

You can also do this automatically using the LiveKit CLI:

```bash
lk app env
```

Run the agent:

```console
python3 agent.py dev
```

This agent requires a frontend application to communicate with. Go to this github link to set up the front end
```bash
https://github.com/plailab/PMI-IOS.git
```
