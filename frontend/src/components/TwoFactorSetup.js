import { useState } from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { toast } from "sonner";
import { ShieldCheck, Copy, Loader2, CheckCircle2, XCircle } from "lucide-react";
import api from "../lib/api";

export default function TwoFactorSetup({ isEnabled, onStatusChange }) {
  const [qrCode, setQrCode] = useState(null);
  const [secret, setSecret] = useState(null);
  const [backupCodes, setBackupCodes] = useState([]);
  const [showBackupCodes, setShowBackupCodes] = useState(false);
  const [verifyCode, setVerifyCode] = useState("");
  const [disableCode, setDisableCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [showDisable, setShowDisable] = useState(false);

  const enable2FA = async () => {
    setLoading(true);
    try {
      const res = await api.post("/auth/2fa/enable");
      setQrCode(res.data.qr_code_base64);
      setSecret(res.data.secret);
      setBackupCodes(res.data.backup_codes);
      toast.success("Scan the QR code with your authenticator app");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to setup 2FA");
    } finally {
      setLoading(false);
    }
  };

  const verify2FA = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post("/auth/2fa/verify", { code: verifyCode });
      toast.success("2FA enabled successfully!");
      setQrCode(null);
      setSecret(null);
      setBackupCodes([]);
      setVerifyCode("");
      onStatusChange?.(true);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Invalid code");
    } finally {
      setLoading(false);
    }
  };

  const disable2FA = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post("/auth/2fa/disable", { code: disableCode });
      toast.success("2FA disabled");
      setShowDisable(false);
      setDisableCode("");
      onStatusChange?.(false);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Invalid code");
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text, label) => {
    navigator.clipboard.writeText(text);
    toast.success(`${label} copied!`);
  };

  if (isEnabled && !showDisable) {
    return (
      <div className="rounded-xl border border-white/10 bg-void-paper p-6" data-testid="2fa-enabled-card">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-emerald-500/10 flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <p className="font-medium text-white">2FA is Active</p>
              <p className="text-sm text-zinc-400">Your account is protected with two-factor authentication</p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowDisable(true)}
            className="border-red-500/30 text-red-400 hover:bg-red-500/10"
            data-testid="disable-2fa-button"
          >
            Disable
          </Button>
        </div>
        {showDisable && (
          <form onSubmit={disable2FA} className="mt-4 flex gap-2">
            <Input
              value={disableCode}
              onChange={(e) => setDisableCode(e.target.value.replace(/\D/g, ''))}
              maxLength={6}
              placeholder="Enter 2FA code"
              className="font-mono"
              data-testid="disable-2fa-code-input"
            />
            <Button type="submit" disabled={loading} variant="destructive" data-testid="confirm-disable-2fa-button">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Confirm"}
            </Button>
          </form>
        )}
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-white/10 bg-void-paper p-6 space-y-6" data-testid="2fa-setup-card">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-electric/10 flex items-center justify-center">
            <ShieldCheck className="w-5 h-5 text-electric" />
          </div>
          <div>
            <p className="font-medium text-white">Two-Factor Authentication</p>
            <p className="text-sm text-zinc-400">Add an extra layer of security to your account</p>
          </div>
        </div>
        {!qrCode && (
          <Button onClick={enable2FA} disabled={loading} className="bg-electric hover:bg-electric/90" data-testid="enable-2fa-button">
            {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
            Enable 2FA
          </Button>
        )}
      </div>

      {qrCode && (
        <div className="space-y-6 border-t border-white/10 pt-6">
          <div className="grid md:grid-cols-2 gap-6">
            <div className="flex flex-col items-center gap-4">
              <p className="text-sm text-zinc-400 text-center">Scan with Google Authenticator, Authy, or any TOTP app</p>
              <div className="bg-white p-3 rounded-xl">
                <img src={qrCode} alt="2FA QR Code" className="w-48 h-48" data-testid="2fa-qr-code" />
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <Label className="text-zinc-400">Manual Entry Key</Label>
                <div className="flex gap-2 mt-1">
                  <Input value={secret || ""} readOnly className="font-mono text-xs" data-testid="2fa-secret-display" />
                  <Button variant="outline" size="icon" onClick={() => copyToClipboard(secret, "Secret key")} data-testid="copy-secret-button">
                    <Copy className="w-4 h-4" />
                  </Button>
                </div>
              </div>

              <div className="rounded-lg bg-amber-500/10 border border-amber-500/20 p-3">
                <p className="text-sm font-medium text-amber-400 mb-2">Save Your Backup Codes</p>
                <p className="text-xs text-zinc-400 mb-3">Use these if you lose access to your authenticator app.</p>
                {showBackupCodes ? (
                  <div className="space-y-2">
                    <div className="bg-void rounded-lg p-3 font-mono text-xs text-zinc-300 grid grid-cols-2 gap-1" data-testid="backup-codes-list">
                      {backupCodes.map((code, i) => (<div key={i}>{code}</div>))}
                    </div>
                    <Button variant="outline" size="sm" onClick={() => copyToClipboard(backupCodes.join("\n"), "Backup codes")} className="w-full" data-testid="copy-backup-codes-button">
                      <Copy className="w-3 h-3 mr-2" /> Copy All
                    </Button>
                  </div>
                ) : (
                  <Button variant="secondary" size="sm" onClick={() => setShowBackupCodes(true)} className="w-full" data-testid="reveal-backup-codes-button">
                    Reveal Backup Codes
                  </Button>
                )}
              </div>
            </div>
          </div>

          <form onSubmit={verify2FA} className="border-t border-white/10 pt-4 space-y-3">
            <Label>Enter 6-digit code from your app</Label>
            <div className="flex gap-2">
              <Input
                value={verifyCode}
                onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, ''))}
                maxLength={6}
                placeholder="000000"
                className="font-mono text-center text-xl tracking-[8px]"
                data-testid="2fa-verify-code-input"
              />
              <Button type="submit" disabled={loading || verifyCode.length !== 6} className="bg-electric hover:bg-electric/90 px-8" data-testid="verify-2fa-button">
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Verify"}
              </Button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
