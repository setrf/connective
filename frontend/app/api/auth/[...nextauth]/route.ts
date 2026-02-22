import NextAuth, { type NextAuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  callbacks: {
    async jwt({ token, account, user }) {
      // On initial sign-in, exchange with backend for a backend JWT
      if (account && user) {
        token.email = user.email;
        token.name = user.name;
        token.picture = user.image;

        try {
          const res = await fetch(`${API_URL}/api/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              token: JSON.stringify({
                email: user.email,
                name: user.name,
                picture: user.image,
              }),
            }),
          });
          if (res.ok) {
            const data = await res.json();
            token.backendToken = data.access_token;
          }
        } catch (e) {
          console.error("Failed to exchange token with backend:", e);
        }
      }
      return token;
    },
    async session({ session, token }) {
      (session as any).backendToken = token.backendToken;
      return session;
    },
  },
  pages: {
    signIn: "/",
  },
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
