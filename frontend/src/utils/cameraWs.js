import { useUserStore } from "@/stores/user";

export function createCameraWs(options) {
  let socket;
  let connected = false;
  let closing = false;
  let reconnectTimer;
  let reconnectAttempts = 0;
  const maxReconnectAttempts = 3;

  return {
    get isConnected() {
      return connected;
    },
    connect() {
      if (socket?.readyState === WebSocket.OPEN) return;
      if (reconnectTimer) {
        window.clearTimeout(reconnectTimer);
        reconnectTimer = undefined;
      }
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const configuredBase = import.meta.env.VITE_WS_BASE_URL;
      const defaultBase = import.meta.env.DEV
        ? "ws://127.0.0.1:8000"
        : `${protocol}//${window.location.host}`;
      const wsBase = configuredBase || defaultBase;
      closing = false;
      const token = encodeURIComponent(useUserStore().token);
      const currentSocket = new WebSocket(
        `${wsBase}/api/detection/camera?token=${token}`,
      );
      socket = currentSocket;
      currentSocket.onopen = () => {
        if (closing) {
          currentSocket.close();
          return;
        }
        connected = true;
        reconnectAttempts = 0;
        currentSocket.send(JSON.stringify({
          type: "config",
          mode: options.mode ?? "cpu",
          conf: options.conf ?? 0.25,
          iou: options.iou ?? 0.45,
          model_id: options.modelId,
        }));
      };
      currentSocket.onmessage = (event) => {
        if (closing) return;
        try {
          const data = JSON.parse(event.data);
          if (data.type === "result") options.onResult?.(data);
          else if (data.type === "config_ok") options.onConfigOk?.(data);
          else if (data.type === "frame_skipped") options.onFrameSkipped?.(data);
          else if (data.type === "error") options.onError?.(data.message);
        } catch {
          options.onError?.("摄像头响应解析失败");
        }
      };
      currentSocket.onerror = () => {
        if (!closing) options.onError?.("WebSocket 连接失败，请检查后端服务");
      };
      currentSocket.onclose = (event) => {
        connected = false;
        options.onClose?.(event);
        if (!closing && reconnectAttempts < maxReconnectAttempts) {
          reconnectAttempts += 1;
          options.onReconnect?.(reconnectAttempts, maxReconnectAttempts);
          reconnectTimer = window.setTimeout(() => {
            reconnectTimer = undefined;
            if (!closing) this.connect();
          }, 500 * reconnectAttempts);
        }
      };
    },
    sendFrame(data) {
      if (closing || !connected || socket?.readyState !== WebSocket.OPEN || !data) return false;
      socket.send(JSON.stringify({ type: "frame", data }));
      return true;
    },
    close() {
      closing = true;
      reconnectAttempts = maxReconnectAttempts;
      if (reconnectTimer) {
        window.clearTimeout(reconnectTimer);
        reconnectTimer = undefined;
      }
      if (socket?.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "close" }));
        const closingSocket = socket;
        window.setTimeout(() => {
          if (closingSocket.readyState === WebSocket.OPEN) closingSocket.close(1000, "Client stopped");
        }, 100);
      } else if (socket?.readyState === WebSocket.CONNECTING) {
        const pendingSocket = socket;
        pendingSocket.addEventListener("open", () => pendingSocket.close(), { once: true });
      }
      socket = undefined;
      connected = false;
    },
  };
}
