"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getToken } from "./auth";

/** Sends signed-out visitors to /login. Returns true once a token is known to exist. */
export function useRequireAuth(): boolean {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (!getToken()) router.replace("/login");
    else setReady(true);
  }, [router]);
  return ready;
}
