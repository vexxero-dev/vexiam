"use client";

import React, { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { CheckCircle2, AlertCircle, ArrowRight, Loader2 } from "lucide-react";

function VerifyContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token");

  const [loading, setLoading] = useState(true);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) {
      setLoading(false);
      setError("No verification token found in URL.");
      return;
    }

    const verify = async () => {
      try {
        await api.post("/auth/verify-email", { token });
        setSuccess(true);
      } catch (err: any) {
        setError(err.response?.data?.detail || "Verification link is invalid or has expired.");
      } finally {
        setLoading(false);
      }
    };

    verify();
  }, [token]);

  return (
    <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl text-center">
      <div className="flex items-center justify-center space-x-3 mb-6">
        <div className="h-10 w-10 bg-indigo-600 rounded-xl flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/30">
          V
        </div>
        <h1 className="text-xl font-bold tracking-tight text-white">VEX IAM</h1>
      </div>

      {loading ? (
        <div className="py-8 flex flex-col items-center space-y-4">
          <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
          <p className="text-slate-300 text-sm">Verifying your email address...</p>
        </div>
      ) : success ? (
        <div className="py-6 space-y-4">
          <div className="w-12 h-12 bg-emerald-500/10 text-emerald-400 rounded-full flex items-center justify-center mx-auto border border-emerald-500/20">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-bold text-white">Email Verified Successfully!</h2>
          <p className="text-sm text-slate-400">
            Your VEX IAM global account is now active and verified.
          </p>
          <button
            onClick={() => router.push("/")}
            className="w-full mt-4 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2.5 rounded-xl transition-all flex items-center justify-center space-x-2 shadow-lg shadow-indigo-600/30"
          >
            <span>Proceed to Dashboard</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      ) : (
        <div className="py-6 space-y-4">
          <div className="w-12 h-12 bg-rose-500/10 text-rose-400 rounded-full flex items-center justify-center mx-auto border border-rose-500/20">
            <AlertCircle className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-bold text-white">Verification Failed</h2>
          <p className="text-sm text-rose-300">{error}</p>
          <button
            onClick={() => router.push("/")}
            className="w-full mt-4 bg-slate-800 hover:bg-slate-700 text-white font-semibold py-2.5 rounded-xl transition-all"
          >
            Back to Sign In
          </button>
        </div>
      )}
    </div>
  );
}

export default function VerifyPage() {
  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center items-center p-6 text-white">
      <Suspense fallback={<div className="text-slate-400 text-sm">Loading...</div>}>
        <VerifyContent />
      </Suspense>
    </div>
  );
}
