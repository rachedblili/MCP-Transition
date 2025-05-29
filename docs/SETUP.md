# 🛠️ Setup Guide: Complete Installation and Configuration

This guide provides step-by-step instructions to get the MCP Transition tutorial running on your system.

---

## 📋 Prerequisites

### System Requirements
- **Python**: 3.8 or higher
- **Operating System**: Windows, macOS, or Linux
- **Memory**: 2GB RAM minimum
- **Storage**: 500MB free space

### API Keys Required
You'll need API keys for external services used in the tutorial:

| Service | Purpose | Required For | Cost |
|---------|---------|--------------|------|
| **OpenAI** | Language model (GPT-4o-mini) | All stages | ~$0.01 per conversation |
| **Tavily** | Web search functionality | Stages 1-4, 6 | Free tier: 1000 searches/month |
| **OpenWeatherMap** | Weather data | Stages 5-6 | Free tier: 1000 calls/day |

---

## 🚀 Installation

### 1. Clone the Repository

```bash
# Using HTTPS
git clone https://github.com/yourusername/MCP-Transition.git
cd MCP-Transition

# Or using SSH
git clone git@github.com:yourusername/MCP-Transition.git
cd MCP-Transition
```

### 2. Create Virtual Environment

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

**Conda (alternative):**
```bash
conda create -n mcp-tutorial python=3.9
conda activate mcp-tutorial
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Dependencies installed:**
- `mcp~=1.9.2` - Official MCP Python SDK
- `starlette` - ASGI framework for SSE server
- `uvicorn` - ASGI server for HTTP deployment
- `aiohttp` - Async HTTP client for API calls
- `python-dotenv~=1.1.0` - Environment variable management
- `nest-asyncio~=1.6.0` - Async compatibility for notebooks

---

## 🔑 API Key Setup

### 1. Create Environment File

```bash
# Copy the example environment file
cp .env.example .env

# Or create manually
touch .env
```

### 2. Configure API Keys

Edit the `.env` file with your API keys:

```bash
# .env file
OPENAI_API_KEY=sk-your-openai-key-here
TAVILY_API_KEY=tvly-your-tavily-key-here
OPENWEATHERMAP_API_KEY=your-openweather-key-here
```

### 3. Obtain API Keys

#### **OpenAI API Key**
1. Visit [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in to your account
3. Navigate to **API Keys** section
4. Click **Create new secret key**
5. Copy the key (starts with `sk-`)
6. Add to `.env` file

**Cost**: Pay-per-use, ~$0.01 per conversation for GPT-4o-mini

#### **Tavily API Key**
1. Visit [Tavily](https://tavily.com/)
2. Sign up for a free account
3. Go to your **Dashboard**
4. Copy your API key (starts with `tvly-`)
5. Add to `.env` file

**Free Tier**: 1000 searches per month

#### **OpenWeatherMap API Key**
1. Visit [OpenWeatherMap](https://openweathermap.org/api)
2. Sign up for a free account
3. Navigate to **API keys** section
4. Copy your default API key
5. Add to `.env` file

**Free Tier**: 1000 API calls per day

---

## ✅ Verification

### 1. Test Basic Setup

```bash
# Test Python and dependencies
python -c "import mcp, aiohttp, starlette; print('✅ All dependencies installed')"

# Test environment variables
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('✅ OpenAI:', bool(os.getenv('OPENAI_API_KEY'))); print('✅ Tavily:', bool(os.getenv('TAVILY_API_KEY'))); print('✅ Weather:', bool(os.getenv('OPENWEATHERMAP_API_KEY')))"
```

### 2. Quick Test Run

```bash
# Test Stage 1 (basic agent)
python naive_agent.py
```

**Expected output:**
```
Pydantic Agent
You: hello
Assistant: Hello! I'm your AI assistant...
```

### 3. Test Each Stage

| Stage | Command | Expected Behavior |
|-------|---------|-------------------|
| **Stage 1** | `python naive_agent.py` | Basic agent with hardcoded tools |
| **Stage 2** | `python improved_agent.py` | Same functionality, better code |
| **Stage 3** | `python mcp_client_stdio.py` | MCP client demo with tool discovery |
| **Stage 4** | `python mcp_agent_with_standard_client.py` | Agent using official MCP library |
| **Stage 5** | See [Stage 5 Setup](#stage-5-sse-weather-service) | Remote weather tools |
| **Stage 6** | See [Stage 6 Setup](#stage-6-multi-transport) | Combined local + remote |

---

## 🌐 Stage-Specific Setup

### Stage 5: SSE Weather Service

Stage 5 requires running two processes:

#### **Terminal 1: Start Weather Server**
```bash
python mcp_server_sse.py
```

**Expected output:**
```
🌤️  Weather MCP Server (SSE) starting...
📡 Server URL: http://localhost:8000/sse
🔧 Tools available: current_weather, weather_forecast, weather_by_coordinates
🌍 Powered by OpenWeatherMap API
⏹️  Press Ctrl+C to stop
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

#### **Terminal 2: Run SSE Agent**
```bash
python mcp_agent_sse.py
```

**Expected output:**
```
🌤️  SSE MCP Agent with Weather Tools
==================================================
✅ SSE weather server is running
🔌 Connecting to weather MCP server...
✅ SSE MCP Agent initialized
🔧 Discovered 3 weather tools:
   • current_weather: Get current weather conditions for any city worldwide
   • weather_forecast: Get a 5-day weather forecast for any city worldwide  
   • weather_by_coordinates: Get current weather by geographic coordinates
💬 Agent ready! Try asking about weather in different cities.
```

### Stage 6: Multi-Transport

Stage 6 also requires the weather server to be running:

```bash
# Terminal 1: Weather server (same as Stage 5)
python mcp_server_sse.py

# Terminal 2: Multi-transport agent
python mcp_agent_multi_transport.py
```

**Expected output:**
```
🚀 Multi-Transport MCP Agent Demo
==================================================
🔍 Checking server availability...
✅ SSE weather server is running
✅ stdio server will be started automatically
🔌 Starting multi-transport MCP connections...
✓ stdio connection established (local tools)
✓ SSE connection established (remote weather service)
✅ Multi-transport agent ready with 5 tools
   📍 Local (stdio): ['date_tool', 'web_search']
   🌐 Remote (SSE): ['current_weather', 'weather_forecast', 'weather_by_coordinates']
```

---

## 🔧 Troubleshooting

### Common Issues

#### **1. Import Errors**

**Error:** `ModuleNotFoundError: No module named 'mcp'`

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

#### **2. API Key Errors**

**Error:** `ValueError: OPENAI_API_KEY environment variable is required`

**Solution:**
```bash
# Check if .env file exists and has correct format
cat .env

# Ensure no spaces around = sign
OPENAI_API_KEY=your_key_here  # ✅ Correct
OPENAI_API_KEY = your_key_here  # ❌ Incorrect
```

#### **3. SSE Connection Issues**

**Error:** `Cannot connect to SSE server`

**Solutions:**
```bash
# Check if weather server is running
curl http://localhost:8000/sse

# Check port availability
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Try different port
# Edit mcp_server_sse.py and mcp_agent_sse.py to use port 8001
```

#### **4. Permission Issues**

**Error:** `Permission denied when running python scripts`

**Solution:**
```bash
# Ensure scripts are executable
chmod +x *.py

# Or run with explicit python
python3 naive_agent.py
```

### API-Specific Issues

#### **OpenAI API**

**Issue**: Rate limiting or quota exceeded
```python
# Test connection
import openai
client = openai.OpenAI()
response = client.models.list()
print("✅ OpenAI connection successful")
```

#### **Tavily Search**

**Issue**: Search failing or quota exceeded
```python
# Test Tavily connection
from tavily import TavilyClient
import os
from dotenv import load_dotenv

load_dotenv()
client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
result = client.search("test query")
print("✅ Tavily connection successful")
```

#### **OpenWeatherMap**

**Issue**: Invalid API key or city not found
```python
# Test weather API
import aiohttp
import asyncio
import os
from dotenv import load_dotenv

async def test_weather():
    load_dotenv()
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")
    
    async with aiohttp.ClientSession() as session:
        url = f"https://api.openweathermap.org/data/2.5/weather"
        params = {"q": "London", "appid": api_key, "units": "metric"}
        
        async with session.get(url, params=params) as response:
            if response.status == 200:
                print("✅ Weather API connection successful")
            else:
                print(f"❌ Weather API error: {response.status}")

asyncio.run(test_weather())
```

---

## 🎯 Development Setup

### Optional: Development Dependencies

For contributing or extending the tutorial:

```bash
# Install development dependencies
pip install black isort mypy pytest pytest-asyncio

# Format code
black *.py
isort *.py

# Type checking
mypy *.py

# Run tests (if available)
pytest
```

### IDE Setup

#### **VS Code**
1. Install Python extension
2. Select your virtual environment (`Ctrl+Shift+P` → "Python: Select Interpreter")
3. Install recommended extensions:
   - Python
   - Pylance
   - Black Formatter

#### **PyCharm**
1. Open project in PyCharm
2. Configure interpreter: Settings → Project → Python Interpreter
3. Select your virtual environment

### Environment Variables in IDE

**VS Code:**
Create `.vscode/settings.json`:
```json
{
    "python.envFile": "${workspaceFolder}/.env"
}
```

**PyCharm:**
1. Run/Debug Configurations
2. Environment variables
3. Load from `.env` file

---

## 🚀 Next Steps

After successful setup:

1. **Follow the Tutorial**: Start with [TUTORIAL.md](./TUTORIAL.md)
2. **Run Each Stage**: Work through stages 1-6 systematically
3. **Experiment**: Modify code and observe behavior changes
4. **Build Extensions**: Create your own MCP servers and tools

### Quick Start Commands

```bash
# Start with the basics
python naive_agent.py

# Progress through stages
python improved_agent.py
python mcp_client_stdio.py
python mcp_agent_with_standard_client.py

# Advanced: Multi-process setup for Stages 5-6
# Terminal 1:
python mcp_server_sse.py

# Terminal 2:
python mcp_agent_sse.py
python mcp_agent_multi_transport.py
```

---

## 📞 Getting Help

### Support Resources

- **Documentation**: [TUTORIAL.md](./TUTORIAL.md) for detailed walkthrough
- **Issues**: [GitHub Issues](../../issues) for bug reports
- **Discussions**: [GitHub Discussions](../../discussions) for questions
- **MCP Community**: [Official MCP Discord/Forum](https://modelcontextprotocol.io/community)

### Common Questions

**Q: Can I use different LLMs besides OpenAI?**
A: Yes! Modify the agent initialization to use other Pydantic AI supported models (Anthropic Claude, local models, etc.)

**Q: How do I add my own tools?**
A: Create new tool functions in the MCP servers and register them in the `handle_list_tools()` function.

**Q: Can I deploy this to production?**
A: The SSE servers (Stage 5-6) are production-ready. Add proper authentication, logging, and monitoring for production use.

---

*Ready to start your MCP journey? Head to [TUTORIAL.md](./TUTORIAL.md) for the complete walkthrough! 🚀*