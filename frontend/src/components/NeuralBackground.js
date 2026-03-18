import { useEffect, useRef, useCallback } from "react";

const NODE_COUNT = 60;
const CONNECTION_DISTANCE = 150;
const MOUSE_RADIUS = 200;

export default function NeuralBackground() {
  const canvasRef = useRef(null);
  const nodesRef = useRef([]);
  const mouseRef = useRef({ x: -1000, y: -1000 });
  const animRef = useRef(null);

  const initNodes = useCallback((w, h) => {
    const nodes = [];
    for (let i = 0; i < NODE_COUNT; i++) {
      nodes.push({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        radius: Math.random() * 2 + 1,
        pulse: Math.random() * Math.PI * 2,
      });
    }
    return nodes;
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    const resize = () => {
      const parent = canvas.parentElement;
      const dpr = window.devicePixelRatio || 1;
      canvas.width = parent.offsetWidth * dpr;
      canvas.height = parent.offsetHeight * dpr;
      canvas.style.width = parent.offsetWidth + "px";
      canvas.style.height = parent.offsetHeight + "px";
      ctx.scale(dpr, dpr);
      nodesRef.current = initNodes(parent.offsetWidth, parent.offsetHeight);
    };

    resize();
    window.addEventListener("resize", resize);

    const handleMouse = (e) => {
      const rect = canvas.getBoundingClientRect();
      mouseRef.current = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    };
    const handleMouseLeave = () => {
      mouseRef.current = { x: -1000, y: -1000 };
    };

    canvas.addEventListener("mousemove", handleMouse);
    canvas.addEventListener("mouseleave", handleMouseLeave);

    const w = () => canvas.width / (window.devicePixelRatio || 1);
    const h = () => canvas.height / (window.devicePixelRatio || 1);

    const draw = () => {
      const cw = w();
      const ch = h();
      ctx.clearRect(0, 0, cw, ch);

      const nodes = nodesRef.current;
      const mouse = mouseRef.current;
      const time = Date.now() * 0.001;

      // Update positions
      for (const node of nodes) {
        node.x += node.vx;
        node.y += node.vy;
        node.pulse += 0.02;

        if (node.x < 0 || node.x > cw) node.vx *= -1;
        if (node.y < 0 || node.y > ch) node.vy *= -1;

        node.x = Math.max(0, Math.min(cw, node.x));
        node.y = Math.max(0, Math.min(ch, node.y));
      }

      // Draw connections
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < CONNECTION_DISTANCE) {
            const alpha = (1 - dist / CONNECTION_DISTANCE) * 0.15;

            // Brighten connections near mouse
            const midX = (nodes[i].x + nodes[j].x) / 2;
            const midY = (nodes[i].y + nodes[j].y) / 2;
            const mouseDist = Math.sqrt(
              (midX - mouse.x) ** 2 + (midY - mouse.y) ** 2
            );
            const mouseBoost =
              mouseDist < MOUSE_RADIUS
                ? (1 - mouseDist / MOUSE_RADIUS) * 0.4
                : 0;

            ctx.beginPath();
            ctx.moveTo(nodes[i].x, nodes[i].y);
            ctx.lineTo(nodes[j].x, nodes[j].y);
            ctx.strokeStyle = `rgba(0, 180, 255, ${alpha + mouseBoost})`;
            ctx.lineWidth = 0.5 + mouseBoost;
            ctx.stroke();
          }
        }
      }

      // Draw nodes
      for (const node of nodes) {
        const mouseDist = Math.sqrt(
          (node.x - mouse.x) ** 2 + (node.y - mouse.y) ** 2
        );
        const mouseBoost =
          mouseDist < MOUSE_RADIUS
            ? (1 - mouseDist / MOUSE_RADIUS) * 0.6
            : 0;
        const pulseSize = Math.sin(node.pulse) * 0.5 + 0.5;
        const r = node.radius + pulseSize * 0.5 + mouseBoost * 2;

        // Outer glow
        const gradient = ctx.createRadialGradient(
          node.x, node.y, 0,
          node.x, node.y, r * 4
        );
        gradient.addColorStop(0, `rgba(0, 180, 255, ${0.15 + mouseBoost * 0.3})`);
        gradient.addColorStop(1, "rgba(0, 180, 255, 0)");
        ctx.beginPath();
        ctx.arc(node.x, node.y, r * 4, 0, Math.PI * 2);
        ctx.fillStyle = gradient;
        ctx.fill();

        // Core
        ctx.beginPath();
        ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(0, 200, 255, ${0.5 + mouseBoost + pulseSize * 0.2})`;
        ctx.fill();
      }

      animRef.current = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      cancelAnimationFrame(animRef.current);
      window.removeEventListener("resize", resize);
      canvas.removeEventListener("mousemove", handleMouse);
      canvas.removeEventListener("mouseleave", handleMouseLeave);
    };
  }, [initNodes]);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 pointer-events-auto"
      style={{ zIndex: 0 }}
      data-testid="neural-background"
    />
  );
}
