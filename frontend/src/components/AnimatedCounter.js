import { useEffect, useRef, useState } from "react";

export default function AnimatedCounter({ value, suffix = "", prefix = "", duration = 2000 }) {
  const [display, setDisplay] = useState(prefix + "0" + suffix);
  const ref = useRef(null);
  const hasAnimated = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasAnimated.current) {
          hasAnimated.current = true;
          animate();
        }
      },
      { threshold: 0.3 }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const animate = () => {
    const numericValue = parseFloat(value.replace(/[^0-9.]/g, ""));
    const isDecimal = value.includes(".");
    const startTime = performance.now();

    const tick = (now) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = numericValue * eased;

      if (isDecimal) {
        setDisplay(prefix + current.toFixed(1) + suffix);
      } else {
        setDisplay(prefix + Math.floor(current).toLocaleString() + suffix);
      }

      if (progress < 1) {
        requestAnimationFrame(tick);
      } else {
        setDisplay(prefix + value + suffix);
      }
    };

    requestAnimationFrame(tick);
  };

  return <span ref={ref}>{display}</span>;
}
