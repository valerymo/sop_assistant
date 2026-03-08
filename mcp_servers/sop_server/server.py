from mcp.server.fastmcp import FastMCP
from .tools import search_sop

mcp = FastMCP("sop-server")

@mcp.tool()
def sop_search(query: str) -> str:
    """Search SOP documentation"""
    return search_sop(query)

if __name__ == "__main__":
    mcp.run()
