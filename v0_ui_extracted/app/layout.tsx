import { Analytics } from '@vercel/analytics/next'
import type { Metadata, Viewport } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'iTantra | LAN Voice Transceiver',
  description: 'Real UDP voice communication console for two laptops on a local network.',
  generator: 'iTantra',
}

export const viewport: Viewport = {
  colorScheme: 'dark',
  themeColor: '#071018',
  userScalable: true,
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}{process.env.NODE_ENV === 'production' && <Analytics />}</body></html>
}
