import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Semantic Media Engine',
  description: 'Discover books and TV shows through natural language queries',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
