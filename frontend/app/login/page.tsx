import AuthForm from "@/components/AuthForm";

export const metadata = { title: "Sign in – Link Shortener" };

export default function LoginPage() {
  return <AuthForm mode="login" />;
}
