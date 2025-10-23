// frontend/src/app/login/error/page.tsx (FINAL)
'use client';
import Link from 'next/link';

export default function LoginErrorPage() {
  return (
    <div className="min-h-screen w-full bg-slate-900 text-white font-sans flex flex-col items-center justify-center text-center p-4">
      <h1 className="text-5xl font-extrabold mb-4">Authentication Error</h1>
      <p className="text-lg text-gray-400 mb-8 max-w-md">
        Something went wrong during the Google login process. This is often caused by a misconfiguration in the Google Cloud Console.
      </p>
      <div className="bg-slate-800 p-6 rounded-lg text-left max-w-lg w-full">
        <h2 className="text-xl font-bold mb-4">Troubleshooting Steps:</h2>
        <ol className="list-decimal list-inside space-y-2 text-gray-300">
          <li>Go to the <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">Google Cloud Console Credentials Page</a>.</li>
          <li>Select your OAuth 2.0 Client ID.</li>
          <li>Under "Authorized redirect URIs", ensure this exact URL is present: <strong>http://127.0.0.1:8000/auth/google/callback</strong></li>
        </ol>
      </div>
      <Link href="/" className="mt-8 px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700">
          Return to Homepage
      </Link>
    </div>
  );
}