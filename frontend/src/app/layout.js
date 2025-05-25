import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'Medi-Scribe',
  description: 'AI-powered medical transcription and SOAP note generation',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <main className="container">
          {children}
        </main>
      </body>
    </html>
  )
}
