import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Sparkles, Search, ChevronLeft, ChevronRight, Clock } from 'lucide-react'
import { ContentCard } from '../components/ContentCard'
import { ContentModal } from '../components/ContentModal'

const pageConfig = {
  news: {
    title: 'NEWS / 新闻',
    subtitle: '最新动态与公告',
    description: '获取 S.H.*.T Space 的最新消息、活动通知和平台公告。',
  },
  questions: {
    title: 'PETRI DISH / 培养皿',
    subtitle: '问答与讨论',
    description: '在这里提出问题、分享观点，与社区成员进行深入交流。',
  },
}

function formatDateTime(value) {
  if (!value) return '尚未同步'
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

export function ContentPage() {
  const { type } = useParams()
  const navigate = useNavigate()
  const [items, setItems] = useState([])
  const [meta, setMeta] = useState({ page: 1, total_pages: 0, total: 0 })
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedItem, setSelectedItem] = useState(null)
  const [lastSync, setLastSync] = useState(null)

  const config = pageConfig[type]

  useEffect(() => {
    async function loadData() {
      setLoading(true)
      try {
        const query = new URLSearchParams({
          page: String(page),
          page_size: '12',
        })
        if (search.trim()) query.set('search', search.trim())

        const response = await fetch(`/api/content/${type}?${query.toString()}`)
        const payload = await response.json()
        setItems(payload.data || [])
        setMeta(payload.meta || { page: 1, total_pages: 0, total: 0 })
      } catch (error) {
        console.error('Failed to load content:', error)
      } finally {
        setLoading(false)
      }
    }

    // 获取同步状态
    async function loadSyncStatus() {
      try {
        const response = await fetch('/api/stats')
        const payload = await response.json()
        setLastSync(payload.data?.scheduler?.last_finished_at)
      } catch (error) {
        console.error('Failed to load sync status:', error)
      }
    }

    loadData()
    loadSyncStatus()
  }, [type, page, search])

  if (!config) {
    return <div>Invalid content type</div>
  }

  return (
    <div className="page-shell">
      <header className="topbar">
        <div className="topbar__inner">
          <button type="button" className="icon-link" onClick={() => navigate('/')}>
            <span>← 返回</span>
          </button>
          <a href="/" className="brandmark">SH*T</a>
          <div className="topbar__actions">
            <button type="button" className="login-button">LOG IN / 登录</button>
          </div>
        </div>
        <nav className="navstrip">
          <a href="/">HOME</a>
          <a href="/content/news" className={type === 'news' ? 'active' : ''}>NEWS / 新闻</a>
          <a href="/content/questions" className={type === 'questions' ? 'active' : ''}>PETRI DISH / 培养皿</a>
          <a href="/">FERMENTATION / 发酵区</a>
        </nav>
      </header>

      <main className="content">
        <div className="breadcrumb">Home &gt; {config.title}</div>

        <section className="hero-section">
          <div className="hero-copy">
            <h1>{config.title}</h1>
            <p>{config.description}</p>
          </div>
        </section>

        <section className="workspace content-page">
          <aside className="control-panel">
            <div className="control-panel__box">
              <div className="control-panel__title">
                <Sparkles size={16} />
                <span>搜索</span>
              </div>
              <label className="search-box">
                <Search size={16} />
                <input
                  type="text"
                  value={search}
                  placeholder="搜索标题 / 内容"
                  onChange={(e) => {
                    setPage(1)
                    setSearch(e.target.value)
                  }}
                />
              </label>
            </div>

            <div className="control-panel__box muted">
              <span className="mini-label">统计</span>
              <p>当前显示 {items.length} 条内容</p>
              <p>总计 {meta.total} 条</p>
              <p style={{ marginTop: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Clock size={14} />
                上次同步: {formatDateTime(lastSync)}
              </p>
              <p style={{ fontSize: '0.8rem', marginTop: '8px', color: 'var(--color-text-muted)' }}>
                数据在服务器启动时自动同步
              </p>
            </div>
          </aside>

          <section className="listing-panel">
            {loading ? (
              <div className="empty-state">正在加载数据...</div>
            ) : items.length === 0 ? (
              <div className="empty-state">暂无内容，请点击同步按钮获取最新数据。</div>
            ) : (
              <>
                <div className="contents-grid">
                  {items.map((item) => (
                    <ContentCard
                      key={item.id}
                      item={item}
                      type={type}
                      onSelect={setSelectedItem}
                    />
                  ))}
                </div>

                <section className="pager">
                  <button
                    type="button"
                    className="pager-button"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1}
                  >
                    <ChevronLeft size={18} />
                  </button>
                  <span>{meta.page} / {meta.total_pages || 1}</span>
                  <button
                    type="button"
                    className="pager-button"
                    onClick={() => setPage((p) => Math.min(meta.total_pages || 1, p + 1))}
                    disabled={page >= (meta.total_pages || 1)}
                  >
                    <ChevronRight size={18} />
                  </button>
                </section>
              </>
            )}
          </section>
        </section>
      </main>

      {selectedItem && (
        <ContentModal
          item={selectedItem}
          type={type}
          onClose={() => setSelectedItem(null)}
        />
      )}
    </div>
  )
}
