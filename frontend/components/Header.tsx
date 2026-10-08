"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clearToken, getToken } from "@/lib/auth";

export default function Header() {
  const router = useRouter();
  const pathname = usePathname();
  const [signedIn, setSignedIn] = useState(false);

  useEffect(() => setSignedIn(Boolean(getToken())), [pathname]);

  function signOut() {
    clearToken();
    router.push("/login");
  }

  return (
    <header className="site-header">
      <Link href="/" className="wordmark">
        <span aria-hidden="true" className="wordmark-mark">/r/</span>
        Link Shortener
      </Link>
      {signedIn && (
        <button type="button" className="btn-quiet" onClick={signOut}>
          Sign out
        </button>
      )}
    </header>
  );
}
