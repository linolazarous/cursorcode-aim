import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Play, Upload } from "lucide-react";
import { Button } from "./ui/button";

export default function DemoVideoModal({ isOpen, onClose }) {
  const [videoError, setVideoError] = useState(false);

  if (!isOpen) return null;

  const videoSrc = `${process.env.PUBLIC_URL}/demo-video.mp4`;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          transition={{ type: "spring", duration: 0.5 }}
          className="relative w-full max-w-4xl bg-void-paper rounded-2xl border border-white/10 overflow-hidden shadow-2xl"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 z-10 p-2 rounded-full bg-black/50 text-white hover:bg-black/70 transition-colors"
            data-testid="close-demo-modal"
          >
            <X className="w-5 h-5" />
          </button>

          {/* Video container */}
          <div className="aspect-video bg-void relative">
            {!videoError ? (
              <video
                className="w-full h-full object-cover"
                controls
                autoPlay
                muted
                playsInline
                onError={() => setVideoError(true)}
                data-testid="demo-video"
              >
                <source src={videoSrc} type="video/mp4" />
                Your browser does not support the video tag.
              </video>
            ) : (
              /* Placeholder when video is not available */
              <div className="absolute inset-0 flex flex-col items-center justify-center bg-gradient-to-br from-void via-void-paper to-void">
                <div className="absolute inset-0 opacity-10">
                  <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(59,130,246,0.3),transparent_70%)]" />
                  <div className="absolute top-1/4 left-1/4 w-64 h-64 bg-electric/20 rounded-full blur-3xl animate-pulse" />
                  <div className="absolute bottom-1/4 right-1/4 w-48 h-48 bg-emerald/20 rounded-full blur-3xl animate-pulse" style={{ animationDelay: "1s" }} />
                </div>

                <div className="relative z-10 text-center px-8">
                  <div className="w-20 h-20 rounded-full bg-electric/20 flex items-center justify-center mx-auto mb-6 border border-electric/30">
                    <Play className="w-10 h-10 text-electric" />
                  </div>
                  
                  <h3 className="font-outfit font-bold text-2xl text-white mb-3">
                    Demo Video Coming Soon
                  </h3>
                  
                  <p className="text-zinc-400 max-w-md mx-auto mb-6">
                    Watch how CursorCode AI transforms your ideas into production-ready applications in minutes.
                  </p>

                  <div className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-zinc-400">
                    <Upload className="w-4 h-4" />
                    <span>Upload <code className="text-electric">demo-video.mp4</code> to <code className="text-electric">/public</code></span>
                  </div>
                </div>

                <div className="absolute bottom-8 left-0 right-0 flex justify-center gap-8">
                  {["Prompt to Code", "AI Agents", "One-Click Deploy"].map((feature, i) => (
                    <div
                      key={feature}
                      className="flex items-center gap-2 text-sm text-zinc-500"
                      style={{ animationDelay: `${i * 0.2}s` }}
                    >
                      <div className="w-1.5 h-1.5 rounded-full bg-electric" />
                      {feature}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Bottom info bar */}
          <div className="px-6 py-4 bg-void-subtle border-t border-white/5 flex items-center justify-between">
            <div>
              <h4 className="font-outfit font-semibold text-white">CursorCode AI Demo</h4>
              <p className="text-sm text-zinc-400">See the future of software development</p>
            </div>
            <Button
              onClick={onClose}
              variant="outline"
              className="border-white/10 text-white hover:bg-white/5"
            >
              Close
            </Button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
