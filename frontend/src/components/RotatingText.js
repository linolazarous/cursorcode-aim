import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

const PROMPTS = [
  "a SaaS dashboard",
  "an e-commerce store",
  "a real-time chat app",
  "a fintech platform",
  "a healthcare portal",
  "an AI-powered API",
];

export default function RotatingText() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setIndex((prev) => (prev + 1) % PROMPTS.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <span className="relative inline-block min-w-[280px] text-left">
      <AnimatePresence mode="wait">
        <motion.span
          key={index}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.4 }}
          className="text-electric inline-block"
        >
          {PROMPTS[index]}
        </motion.span>
      </AnimatePresence>
    </span>
  );
}
