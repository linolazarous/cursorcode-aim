import { useEffect, useState, useCallback } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "../components/ui/button";
import { useAuth } from "../context/AuthContext";
import api from "../lib/api";
import { toast } from "sonner";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";
import Logo from "../components/Logo";

export default function VerifyEmailPage() {

  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { refreshUser } = useAuth();

  const [status,setStatus] = useState("verifying")
  const [message,setMessage] = useState("")



  // =====================================================
  // VERIFY EMAIL FUNCTION
  // =====================================================

  const verifyEmail = useCallback(async (token) => {

    try {

      const res = await api.get(`/api/auth/verify-email`,{
        params:{ token }
      })

      setStatus("success")

      setMessage(
        res?.data?.message || "Your email has been verified successfully."
      )

      toast.success("Email verified successfully!")

      await refreshUser()

      setTimeout(()=>{
        navigate("/dashboard")
      },2000)

    }

    catch(error){

      console.error("Email verification error:",error)

      setStatus("error")

      const errorMessage =
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        "Verification link is invalid or expired."

      setMessage(errorMessage)

      toast.error(errorMessage)

    }

  },[refreshUser,navigate])



  // =====================================================
  // READ TOKEN FROM URL
  // =====================================================

  useEffect(()=>{

    const token = searchParams.get("token")

    if(!token){

      setStatus("error")

      setMessage("Invalid verification link")

      return
    }

    verifyEmail(token)

  },[searchParams,verifyEmail])



  return (

    <div className="min-h-screen bg-void noise-bg flex items-center justify-center p-8">

      <motion.div
        initial={{opacity:0,scale:0.95}}
        animate={{opacity:1,scale:1}}
        className="max-w-md w-full"
      >

        <div className="text-center mb-8">
          <Logo size="large" className="justify-center"/>
        </div>


        <div className="bg-void-paper border border-white/5 rounded-xl p-8 text-center">

          {/* VERIFYING */}

          {status === "verifying" && (

            <>
              <Loader2 className="w-16 h-16 text-electric mx-auto mb-4 animate-spin"/>

              <h2 className="font-outfit font-bold text-2xl text-white mb-2">
                Verifying your email...
              </h2>

              <p className="text-zinc-400">
                Please wait a moment
              </p>
            </>

          )}



          {/* SUCCESS */}

          {status === "success" && (

            <>
              <div className="w-16 h-16 rounded-full bg-emerald/20 flex items-center justify-center mx-auto mb-4">

                <CheckCircle2 className="w-10 h-10 text-emerald"/>

              </div>

              <h2 className="font-outfit font-bold text-2xl text-white mb-2">
                Email Verified!
              </h2>

              <p className="text-zinc-400 mb-6">
                {message}
              </p>

              <Button
                onClick={()=>navigate("/dashboard")}
                className="bg-electric hover:bg-electric/90 text-white"
              >
                Go to Dashboard
              </Button>

            </>

          )}



          {/* ERROR */}

          {status === "error" && (

            <>
              <div className="w-16 h-16 rounded-full bg-red-500/20 flex items-center justify-center mx-auto mb-4">

                <XCircle className="w-10 h-10 text-red-500"/>

              </div>

              <h2 className="font-outfit font-bold text-2xl text-white mb-2">
                Verification Failed
              </h2>

              <p className="text-zinc-400 mb-6">
                {message}
              </p>

              <Button
                onClick={()=>navigate("/login")}
                variant="outline"
                className="border-white/10 text-white hover:bg-white/5"
              >
                Back to Login
              </Button>

            </>

          )}

        </div>

      </motion.div>

    </div>

  )

}
