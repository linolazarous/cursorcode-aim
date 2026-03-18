import { useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { Label } from "../components/ui/label";
import { toast } from "sonner";
import { ArrowLeft, Mail, MessageSquare, Send, Loader2, CheckCircle2, MapPin, Clock } from "lucide-react";
import Logo from "../components/Logo";

export default function ContactPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name || !email || !message) return toast.error("Please fill in all required fields");
    setSending(true);
    // Simulate sending (replace with real API when SendGrid is configured)
    await new Promise(r => setTimeout(r, 1500));
    setSent(true);
    toast.success("Message sent! We'll get back to you within 24 hours.");
    setSending(false);
  };

  return (
    <div className="min-h-screen bg-void noise-bg">
      <header className="border-b border-white/5">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/"><Logo size="default" /></Link>
          <Link to="/" className="text-sm text-zinc-400 hover:text-white flex items-center gap-2"><ArrowLeft className="w-4 h-4" /> Back</Link>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-12">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <div className="text-center mb-12">
            <h1 className="font-outfit font-bold text-4xl text-white mb-3">Get in Touch</h1>
            <p className="text-zinc-400 max-w-lg mx-auto">Have a question, feedback, or need enterprise support? We'd love to hear from you.</p>
          </div>

          <div className="grid md:grid-cols-5 gap-10">
            {/* Contact Info */}
            <div className="md:col-span-2 space-y-6">
              <div className="p-6 rounded-xl border border-white/5 bg-void-paper space-y-6">
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-lg bg-electric/10 flex items-center justify-center shrink-0">
                    <Mail className="w-5 h-5 text-electric" />
                  </div>
                  <div>
                    <p className="font-medium text-white text-sm">Email</p>
                    <a href="mailto:hello@cursorcode.ai" className="text-zinc-400 text-sm hover:text-electric" data-testid="contact-email">hello@cursorcode.ai</a>
                  </div>
                </div>

                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center shrink-0">
                    <MessageSquare className="w-5 h-5 text-purple-400" />
                  </div>
                  <div>
                    <p className="font-medium text-white text-sm">Support</p>
                    <a href="mailto:support@cursorcode.ai" className="text-zinc-400 text-sm hover:text-electric">support@cursorcode.ai</a>
                  </div>
                </div>

                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center shrink-0">
                    <Clock className="w-5 h-5 text-emerald-400" />
                  </div>
                  <div>
                    <p className="font-medium text-white text-sm">Response Time</p>
                    <p className="text-zinc-400 text-sm">Within 24 hours (business days)</p>
                  </div>
                </div>

                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center shrink-0">
                    <MapPin className="w-5 h-5 text-amber-400" />
                  </div>
                  <div>
                    <p className="font-medium text-white text-sm">Enterprise Inquiries</p>
                    <a href="mailto:enterprise@cursorcode.ai" className="text-zinc-400 text-sm hover:text-electric">enterprise@cursorcode.ai</a>
                  </div>
                </div>
              </div>
            </div>

            {/* Contact Form */}
            <div className="md:col-span-3">
              {sent ? (
                <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="p-10 rounded-xl border border-emerald-500/20 bg-emerald-500/5 text-center" data-testid="contact-success">
                  <CheckCircle2 className="w-14 h-14 text-emerald-400 mx-auto mb-4" />
                  <h2 className="text-2xl font-bold text-white mb-2">Message Sent!</h2>
                  <p className="text-zinc-400 mb-6">We'll get back to you within 24 hours.</p>
                  <Button onClick={() => { setSent(false); setName(""); setEmail(""); setSubject(""); setMessage(""); }} variant="outline" className="border-white/10">Send Another</Button>
                </motion.div>
              ) : (
                <form onSubmit={handleSubmit} className="p-6 rounded-xl border border-white/5 bg-void-paper space-y-5" data-testid="contact-form">
                  <div className="grid sm:grid-cols-2 gap-4">
                    <div>
                      <Label>Name *</Label>
                      <Input value={name} onChange={e => setName(e.target.value)} placeholder="Your name" required data-testid="contact-name" />
                    </div>
                    <div>
                      <Label>Email *</Label>
                      <Input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" required data-testid="contact-email-input" />
                    </div>
                  </div>

                  <div>
                    <Label>Subject</Label>
                    <Input value={subject} onChange={e => setSubject(e.target.value)} placeholder="What's this about?" data-testid="contact-subject" />
                  </div>

                  <div>
                    <Label>Message *</Label>
                    <Textarea value={message} onChange={e => setMessage(e.target.value)} placeholder="Tell us more..." className="min-h-[140px]" required data-testid="contact-message" />
                  </div>

                  <Button type="submit" disabled={sending} className="w-full bg-electric hover:bg-electric/90 text-white shadow-glow h-12" data-testid="contact-submit">
                    {sending ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Sending...</> : <><Send className="w-4 h-4 mr-2" /> Send Message</>}
                  </Button>
                </form>
              )}
            </div>
          </div>
        </motion.div>
      </main>
    </div>
  );
}
