# 🚀 From Naive Agent to MCP Mastery

**A Comprehensive Tutorial for Building Model Context Protocol (MCP) Enabled AI Agents**

---

## 🌟 Overview

This repository provides a **complete, hands-on journey** from building a simple AI agent to creating sophisticated, distributed systems using the Model Context Protocol (MCP). Through 6 carefully crafted iterations, you'll master the fundamental concepts and advanced patterns of MCP architecture.

### 🎯 What You'll Learn

- **Agent Architecture Evolution**: From monolithic to modular, protocol-driven design
- **MCP Protocol Mastery**: stdio and SSE transports, tool discovery, session management
- **Production Patterns**: Error handling, structured data, multi-transport composition
- **Real-world Integration**: External APIs, remote services, distributed tool ecosystems

---

## 🗺️ The Journey

<table>
<tr>
<td width="60">🏁</td>
<td><strong>Stage 1</strong></td>
<td><a href="#stage-1-naive-implementation">Naive Agent</a></td>
<td>Simple agent with hardcoded tools</td>
</tr>
<tr>
<td>🔧</td>
<td><strong>Stage 2</strong></td>
<td><a href="#stage-2-improved-architecture">Improved Agent</a></td>
<td>Async patterns and code cleanup</td>
</tr>
<tr>
<td>🔌</td>
<td><strong>Stage 3</strong></td>
<td><a href="#stage-3-mcp-foundation">MCP Foundation</a></td>
<td>stdio server and custom MCP client</td>
</tr>
<tr>
<td>📚</td>
<td><strong>Stage 4</strong></td>
<td><a href="#stage-4-official-library">Official Library</a></td>
<td>Using Anthropic's MCP Python SDK</td>
</tr>
<tr>
<td>🌐</td>
<td><strong>Stage 5</strong></td>
<td><a href="#stage-5-remote-services">Remote Services</a></td>
<td>SSE transport with weather API integration</td>
</tr>
<tr>
<td>🌍</td>
<td><strong>Stage 6</strong></td>
<td><a href="#stage-6-multi-transport">Multi-Transport</a></td>
<td>Unified agent with local + remote tools</td>
</tr>
</table>

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- API Keys: [Tavily](https://tavily.com) (web search), [OpenWeatherMap](https://openweathermap.org/api) (weather)
- OpenAI API access

### 1-Minute Setup
```bash
# Clone and setup
git clone <repository-url>
cd MCP-Transition
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run any stage
python naive_agent.py           # Stage 1
python improved_agent.py        # Stage 2
python mcp_agent_sse.py         # Stage 5 (requires weather server)
```

### Environment Variables
```bash
# .env file
OPENAI_API_KEY=your_openai_key_here
TAVILY_API_KEY=your_tavily_key_here
OPENWEATHERMAP_API_KEY=your_weather_key_here
```

---

## 📖 Detailed Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| **[📋 Setup Guide](./docs/SETUP.md)** | Complete installation and configuration | All users |
| **[🎓 Step-by-Step Tutorial](./docs/TUTORIAL.md)** | Detailed code walkthrough with highlights | Developers |
| **[🔧 MCP Protocol Guide](./docs/MCP_CONCEPTS.md)** | Deep dive into MCP internals | Advanced users |
| **[🌐 Deployment Guide](./docs/DEPLOYMENT.md)** | Production deployment patterns | DevOps teams |

---

## 📁 Repository Structure

```
MCP-Transition/
├── README.md                              # This file
├── requirements.txt                       # Python dependencies
├── prompts.py                            # Shared prompt templates
│
├── 🏁 STAGE 1: Naive Implementation
│   └── naive_agent.py                    # Basic agent with hardcoded tools
│
├── 🔧 STAGE 2: Improved Architecture  
│   └── improved_agent.py                 # Async patterns and cleanup
│
├── 🔌 STAGE 3: MCP Foundation
│   ├── mcp_server_stdio.py              # Local MCP server (stdio transport)
│   └── mcp_client_stdio.py              # Custom MCP client implementation
│
├── 📚 STAGE 4: Official Library
│   └── mcp_agent_with_standard_client.py # Using official Anthropic MCP SDK
│
├── 🌐 STAGE 5: Remote Services
│   ├── mcp_server_sse.py                # Remote weather server (SSE transport)
│   └── mcp_agent_sse.py                 # SSE-based agent
│
├── 🌍 STAGE 6: Multi-Transport
│   └── mcp_agent_multi_transport.py     # Unified local + remote agent
│
└── docs/                                 # Detailed documentation
    ├── SETUP.md                         # Installation guide
    ├── TUTORIAL.md                      # Step-by-step code walkthrough
    ├── MCP_CONCEPTS.md                  # Protocol deep dive
    └── DEPLOYMENT.md                    # Production deployment
```

---

## 🎯 Stage Overview

### Stage 1: Naive Implementation
**File:** `naive_agent.py`
- Basic **PydanticAI** agent with hardcoded tools
- Synchronous execution with async workarounds  
- Direct API calls without abstraction

**Why PydanticAI?** I chose PydanticAI as the starting framework because it provides the cleanest, non-vendor-specific approach to building AI agents. Unlike framework-specific solutions, PydanticAI offers excellent separation between conversation management and tooling, making it ideal for demonstrating MCP integration patterns.

**Alternative Frameworks:** This is just one of many possible implementations! For the same agent implemented across **8 different frameworks** (LangChain, LangGraph, CrewAI, Llama-Index, OpenAI Assistants, Anthropic, and Atomic Agents), check out my [**Agent Framework Comparison Repository**](https://github.com/rachedblili/AgentExamples). You can use any of these as your starting point for MCP integration.

**Key Concepts:** Basic agent architecture, tool registration, conversation flow

---

### Stage 2: Improved Architecture
**File:** `improved_agent.py`
- Proper async/await patterns
- Better error handling and type hints
- Cleaner code structure and formatting

**Key Concepts:** Async programming, code quality, maintainable architecture

---

### Stage 3: MCP Foundation
**Files:** `mcp_server_stdio.py`, `mcp_client_stdio.py`
- First MCP implementation using stdio transport
- Custom client with full protocol implementation
- Tool discovery and JSON-RPC 2.0 messaging

**Key Concepts:** MCP protocol, stdio transport, JSON-RPC, tool discovery

---

### Stage 4: Official Library
**File:** `mcp_agent_with_standard_client.py`
- Replacement of custom client with official Anthropic MCP SDK
- Simplified codebase (~100 lines reduction)
- Production-ready protocol compliance

**Key Concepts:** Official libraries vs custom implementation, code simplification

---

### Stage 5: Remote Services
**Files:** `mcp_server_sse.py`, `mcp_agent_sse.py`
- HTTP-based MCP server with Server-Sent Events
- Real-world API integration (OpenWeatherMap)
- Remote deployment capabilities

**Key Concepts:** SSE transport, remote services, external API integration

---

### Stage 6: Multi-Transport
**File:** `mcp_agent_multi_transport.py`
- Simultaneous connection to multiple MCP servers
- Mixed local (stdio) and remote (SSE) tools
- Unified tool interface and session management

**Key Concepts:** Multi-transport architecture, tool composition, distributed systems

---

## 🛠️ Available Tools by Stage

<table>
<tr><th>Stage</th><th>Tools</th><th>Transport</th><th>Location</th></tr>
<tr>
<td>1-2</td>
<td>📅 Date, 🔍 Web Search</td>
<td>Direct calls</td>
<td>Local</td>
</tr>
<tr>
<td>3-4</td>
<td>📅 Date, 🔍 Web Search</td>
<td>stdio MCP</td>
<td>Local subprocess</td>
</tr>
<tr>
<td>5</td>
<td>🌤️ Current Weather, 📊 Forecast, 🗺️ Coordinates</td>
<td>SSE MCP</td>
<td>Remote HTTP server</td>
</tr>
<tr>
<td>6</td>
<td>📅 Date, 🔍 Web Search, 🌤️ Weather Tools</td>
<td>stdio + SSE MCP</td>
<td>Local + Remote</td>
</tr>
</table>

---

## 🎓 Learning Path Recommendations

### **Beginner**: Start with the Basics
1. Run Stages 1-2 to understand agent fundamentals
2. Read [Setup Guide](./docs/SETUP.md) for environment configuration
3. Follow [Tutorial](./docs/TUTORIAL.md) through Stage 3

### **Intermediate**: Dive into MCP
1. Complete Stages 3-4 to master MCP basics
2. Study [MCP Protocol Guide](./docs/MCP_CONCEPTS.md)
3. Experiment with Stage 5 for remote capabilities

### **Advanced**: Build Production Systems
1. Master Stage 6 multi-transport patterns
2. Review [Deployment Guide](./docs/DEPLOYMENT.md)
3. Extend with your own MCP servers and tools

---

## 🤝 Contributing

We welcome contributions! Here are some ways to help:

- **🐛 Bug Reports**: Found an issue? [Open an issue](../../issues)
- **💡 Feature Requests**: Ideas for new stages or improvements
- **📖 Documentation**: Help improve guides and examples
- **🔧 Code**: Submit PRs for bug fixes or enhancements

### Development Setup
```bash
# Fork and clone the repository
git clone https://github.com/yourusername/MCP-Transition.git
cd MCP-Transition

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If available

# Run tests
python -m pytest tests/  # If tests are available
```

---

## 📚 Additional Resources

### MCP Ecosystem
- **[Official MCP Specification](https://spec.modelcontextprotocol.io/)** - Complete protocol documentation
- **[Anthropic MCP Repository](https://github.com/modelcontextprotocol/python-sdk)** - Official Python SDK
- **[MCP Community](https://github.com/modelcontextprotocol/servers)** - Community MCP servers

### Related Technologies
- **[Pydantic AI](https://ai.pydantic.dev/)** - AI agent framework used in examples
- **[OpenAI API](https://platform.openai.com/docs)** - Language model integration
- **[Tavily API](https://docs.tavily.com/)** - Web search capabilities

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Anthropic** for creating the Model Context Protocol and providing excellent documentation
- **Pydantic AI** team for the elegant agent framework
- **Community contributors** who helped improve this tutorial

---

<div align="center">

**Ready to start your MCP journey?**

[📋 Setup Guide](./docs/SETUP.md) → [🎓 Tutorial](./docs/TUTORIAL.md) → [🚀 Build Something Amazing](./docs/DEPLOYMENT.md)

</div>