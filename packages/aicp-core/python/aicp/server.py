import asyncio
import logging
from aicp.websocket_transport import AICPWebSocketServer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    server = AICPWebSocketServer(host="0.0.0.0", port=8765)
    await server.start()
    logger.info("🚀 AICP WebSocket Server running on ws://0.0.0.0:8765")
    logger.info("📊 Waiting for agents to connect...")
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutting down server...")

if __name__ == "__main__":
    asyncio.run(main())
