import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { toast } from "sonner";
import {
  ArrowLeft,
  Eye,
  EyeOff,
  Loader2,
  CheckCircle2,
  Github
} from "lucide-react";
import Logo from "../components/Logo";

export default function SignupPage() {

  const navigate = useNavigate()

  const [name,setName] = useState("")
  const [email,setEmail] = useState("")
  const [password,setPassword] = useState("")
  const [showPassword,setShowPassword] = useState(false)

  const [loading,setLoading] = useState(false)
  const [githubLoading,setGithubLoading] = useState(false)
  const [googleLoading,setGoogleLoading] = useState(false)

  const API = process.env.REACT_APP_API_URL

  // =====================================================
  // EMAIL SIGNUP
  // =====================================================

  const handleSubmit = async (e) => {

    e.preventDefault()

    setLoading(true)

    try{

      const res = await fetch(`${API}/api/auth/signup`,{
        method:"POST",
        headers:{
          "Content-Type":"application/json"
        },
        body:JSON.stringify({
          name,
          email,
          password
        })
      })

      const data = await res.json()

      if(!res.ok){
        throw new Error(data.detail || "Signup failed")
      }

      localStorage.setItem("token",data.access_token)

      toast.success("Account created successfully!")

      navigate("/dashboard")

    }catch(err){

      toast.error(err.message)

    }finally{

      setLoading(false)

    }

  }


  // =====================================================
  // GITHUB OAUTH
  // =====================================================

  const handleGithubSignup = () => {

    setGithubLoading(true)

    window.location.href = `${API}/auth/github`

  }


  // =====================================================
  // GOOGLE OAUTH
  // =====================================================

  const handleGoogleSignup = () => {

    setGoogleLoading(true)

    window.location.href = `${API}/auth/google`

  }


  return (

    <div className="min-h-screen bg-void noise-bg flex">

      {/* LEFT PANEL */}

      <div className="hidden lg:flex lg:w-1/2 relative bg-void-paper border-r border-white/5">

        <div className="absolute inset-0 bg-hero-glow" />

        <div className="relative z-10 flex flex-col justify-between p-12 w-full">

          <Link to="/">
            <Logo size="large"/>
          </Link>

          <div>

            <h2 className="font-outfit font-bold text-4xl text-white mb-4">
              Start building
              <br/>
              <span className="text-electric">in minutes</span>
            </h2>

            <p className="text-zinc-400 text-lg max-w-md mb-8">
              Get 10 free AI credits to create your first project.
            </p>

            <div className="space-y-4">

              {[
                "Multi-agent AI system powered by xAI Grok",
                "One-click deployment",
                "Full-stack apps from plain English"
              ].map((feature)=>(
                <div key={feature} className="flex items-center gap-3">
                  <CheckCircle2 className="w-5 h-5 text-emerald"/>
                  <span className="text-white">{feature}</span>
                </div>
              ))}

            </div>

          </div>

          <p className="text-sm text-zinc-500">
            © 2025 CursorCode AI
          </p>

        </div>

      </div>


      {/* RIGHT PANEL */}

      <div className="w-full lg:w-1/2 flex items-center justify-center p-8">

        <motion.div
          initial={{opacity:0,y:20}}
          animate={{opacity:1,y:0}}
          className="w-full max-w-md"
        >

          <Link to="/" className="flex lg:hidden mb-8">
            <Logo size="default"/>
          </Link>


          <Link
            to="/"
            className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-white mb-8"
          >
            <ArrowLeft className="w-4 h-4"/>
            Back
          </Link>


          <h1 className="font-outfit font-bold text-3xl text-white mb-2">
            Create your account
          </h1>

          <p className="text-zinc-400 mb-8">
            Start building with free AI credits
          </p>


          {/* GOOGLE */}

          <Button
            onClick={handleGoogleSignup}
            disabled={googleLoading}
            className="w-full h-12 mb-4"
          >

            {googleLoading ? (
              <Loader2 className="w-5 h-5 animate-spin"/>
            ) : (
              "Continue with Google"
            )}

          </Button>


          {/* GITHUB */}

          <Button
            onClick={handleGithubSignup}
            disabled={githubLoading}
            variant="outline"
            className="w-full h-12 mb-6"
          >

            {githubLoading ? (
              <Loader2 className="w-5 h-5 animate-spin"/>
            ) : (
              <Github className="w-5 h-5 mr-2"/>
            )}

            Continue with GitHub

          </Button>


          {/* DIVIDER */}

          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-white/10"/>
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="bg-void px-4 text-zinc-500">
                or continue with email
              </span>
            </div>
          </div>


          {/* EMAIL FORM */}

          <form onSubmit={handleSubmit} className="space-y-4">

            <div>
              <Label>Name</Label>
              <Input
                value={name}
                onChange={(e)=>setName(e.target.value)}
                required
              />
            </div>

            <div>
              <Label>Email</Label>
              <Input
                type="email"
                value={email}
                onChange={(e)=>setEmail(e.target.value)}
                required
              />
            </div>

            <div>
              <Label>Password</Label>

              <div className="relative">

                <Input
                  type={showPassword ? "text":"password"}
                  value={password}
                  onChange={(e)=>setPassword(e.target.value)}
                  required
                />

                <button
                  type="button"
                  onClick={()=>setShowPassword(!showPassword)}
                  className="absolute right-3 top-3"
                >
                  {showPassword ? <EyeOff size={18}/> : <Eye size={18}/>}
                </button>

              </div>

            </div>


            <Button
              type="submit"
              disabled={loading}
              className="w-full h-12 bg-electric text-white"
            >

              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin"/>
                  Creating account...
                </>
              ) : (
                "Create account"
              )}

            </Button>

          </form>


          <p className="text-center text-zinc-400 mt-8">
            Already have an account?{" "}
            <Link to="/login" className="text-electric hover:underline">
              Sign in
            </Link>
          </p>

        </motion.div>

      </div>

    </div>

  )

}
