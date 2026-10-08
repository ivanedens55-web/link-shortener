import Link from "next/link";

export default function NotFound() {
  return (
    <main className="page">
      <h1>Page not found</h1>
      <p><Link href="/">Go to your links</Link></p>
    </main>
  );
}
