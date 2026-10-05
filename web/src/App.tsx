import { useEffect } from 'react'
import { Routes, Route, useLocation } from 'react-router'
import { AppProvider } from './lib/state'
import { TopNav } from './components/TopNav'
import Home from './pages/Home'
import Report from './pages/Report'
import Vision from './pages/Vision'

/** 路由切换回到页面顶部；带 hash（如 /#analyze）则滚动到对应区块 */
function ScrollToTop() {
  const { pathname, hash } = useLocation()
  useEffect(() => {
    if (hash) {
      const el = document.getElementById(hash.slice(1))
      if (el) {
        el.scrollIntoView()
        return
      }
    }
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' as ScrollBehavior })
  }, [pathname, hash])
  return null
}

export default function App() {
  return (
    <AppProvider>
      <ScrollToTop />
      <TopNav />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/report" element={<Report />} />
        <Route path="/vision" element={<Vision />} />
      </Routes>
    </AppProvider>
  )
}
