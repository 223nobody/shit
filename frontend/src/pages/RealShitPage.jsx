import { useEffect, useState } from 'react'
import {
  ChevronLeft,
  ChevronRight,
  Clock3,
  ExternalLink,
  FileImage,
  Megaphone,
  Menu,
  MessageCircle,
  RefreshCcw,
  Search,
  Sparkles,
  Star,
} from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { ArticleDetailModal } from '../components/ArticleDetailModal'
import '../App.css'

/** 与源站 /realshit 同源列表语义（后端 GET /api/realshit → tag=hardcore） */
const TAG_LABEL = '严谨论证'

const disciplineLabels = {
  interdisciplinary: '交叉学科',
  social: '社会学',
  management: '管理学',
  economics: '经济学',
  law: '法学',
  literature: '文学',
  engineering: '工程学',
  medicine: '医学',
}

/** 源站 zones：latrine / septic / sediment / stone */
const zoneLabels = {
  latrine: '发酵区',
  septic: '化腐区',
  sediment: '沉定区',
  stone: '构石区',
  published: '已发表',
}

function formatDate(value) {
  if (!value) return '未知时间'
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(value))
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

function formatClock(date) {
  return new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(date)
}

function authorDisplayName(article) {
  if (article.author && typeof article.author === 'object') {
    return article.author.display_name || '匿名作者'
  }
  return article.author_name || '匿名作者'
}

function zoneKey(article) {
  return article.zones || article.zone || ''
}

function RealShitRow({ article, onSelect, zoneLabel, disciplineLabel }) {
  const score = Number(article.avg_score || 0)
  const ratings = Number(article.rating_count || 0)
  const comments = Number(article.comment_count || 0)
  const sourceArticleUrl = `https://shitspace.xyz/articles/${article.id}`

  return (
    <div className="realshit-feed__row-wrap">
      <button
        type="button"
        className="realshit-feed__row"
        onClick={() => onSelect(article.id)}
      >
        <div className="realshit-feed__thumb">
          {article.cover_image_url ? (
            <img src={article.cover_image_url} alt="" />
          ) : (
            <div className="realshit-feed__thumb-fallback">
              <FileImage size={28} />
            </div>
          )}
        </div>
        <div className="realshit-feed__body">
          <span className="realshit-feed__kicker">{TAG_LABEL}</span>
          <h2 className="realshit-feed__title">{article.title}</h2>
          <div className="realshit-feed__stats">
            <span className="realshit-feed__stat" title="均分（源站 avg_score）">
              <Star size={13} aria-hidden />
              {score > 0 ? score.toFixed(2) : '—'}
            </span>
            <span className="realshit-feed__stat" title="评分条数">
              {ratings} 评分
            </span>
            <span className="realshit-feed__stat">
              <MessageCircle size={13} aria-hidden />
              {comments} 评论
            </span>
          </div>
          <div className="realshit-feed__meta">
            <span>{authorDisplayName(article)}</span>
            <span>{disciplineLabel}</span>
            <span>{zoneLabel}</span>
            <span>{formatDate(article.approved_at || article.created_at)}</span>
            <span>{article.page_count || 0} 页</span>
          </div>
        </div>
        <div className="realshit-feed__chev" aria-hidden>
          →
        </div>
      </button>
      <a
        className="realshit-feed__source"
        href={sourceArticleUrl}
        target="_blank"
        rel="noreferrer"
        title="在 shitspace.xyz 打开同一篇"
      >
        <ExternalLink size={14} aria-hidden />
        源站
      </a>
    </div>
  )
}

export function RealShitPage() {
  const [filters, setFilters] = useState({
    search: '',
  })
  const [page, setPage] = useState(1)
  const [articles, setArticles] = useState([])
  const [meta, setMeta] = useState({ page: 1, total_pages: 0, total: 0 })
  const [stats, setStats] = useState(null)
  const [selectedArticle, setSelectedArticle] = useState(null)
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [clock, setClock] = useState(new Date())
  const location = useLocation()
  const path = location.pathname

  useEffect(() => {
    const timer = window.setInterval(() => {
      setClock(new Date())
    }, 1000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    const controller = new AbortController()

    async function loadData() {
      setLoading(true)

      const query = new URLSearchParams({
        page: String(page),
        page_size: '10',
      })

      if (filters.search.trim()) query.set('search', filters.search.trim())

      const [articlesResponse, statsResponse] = await Promise.all([
        fetch(`/api/realshit?${query.toString()}`, { signal: controller.signal }),
        fetch('/api/stats', { signal: controller.signal }),
      ])

      const articlesPayload = await articlesResponse.json()
      const statsPayload = await statsResponse.json()

      setArticles(articlesPayload.data || [])
      const total = Number(articlesPayload.count ?? 0)
      const totalPages = Number(articlesPayload.total_pages ?? 0)
      const currentPage = Number(articlesPayload.page ?? page)
      setMeta({
        page: currentPage,
        total_pages: totalPages,
        total,
      })
      setStats(statsPayload.data || null)
      setLoading(false)
    }

    loadData().catch((error) => {
      if (error.name !== 'AbortError') setLoading(false)
    })

    return () => controller.abort()
  }, [filters, page])

  async function openArticle(articleId) {
    const response = await fetch(`/api/articles/${articleId}`)
    const payload = await response.json()
    setSelectedArticle(payload.data)
  }

  async function syncArticles() {
    setSyncing(true)
    try {
      await fetch('/api/sync', { method: 'POST' })
      setPage(1)
      setFilters((current) => ({ ...current }))
      const statsResponse = await fetch('/api/stats')
      const statsPayload = await statsResponse.json()
      setStats(statsPayload.data || null)
    } finally {
      setSyncing(false)
    }
  }

  return (
    <div className="page-shell page-shell--realshit">
      <header className="topbar">
        <div className="topbar__inner">
          <button type="button" className="icon-link">
            <Menu size={18} />
            <span>MENU</span>
          </button>
          <Link to="/" className="brandmark">
            <span className="brandmark__main">S.H.*.T</span>
            <span className="brandmark__sub">Sciences · Humanities · Information · Technology</span>
          </Link>
          <div className="topbar__actions">
            <button type="button" className="icon-button" aria-label="搜索">
              <Search size={18} />
            </button>
            <button type="button" className="login-button">
              LOG IN / 登录
            </button>
          </div>
        </div>
        <nav className="navstrip">
          <Link to="/" className={path === '/' ? 'active' : ''}>
            HOME
          </Link>
          <Link to="/content/news" className={path.startsWith('/content/news') ? 'active' : ''}>
            NEWS / 新闻
          </Link>
          <Link to="/content/questions" className={path.startsWith('/content/questions') ? 'active' : ''}>
            PETRI DISH / 培养皿
          </Link>
          <Link to="/realshit" className={path === '/realshit' ? 'active' : ''}>
            REALSHIT / 构石
          </Link>
          <Link to="/fermentation" className={path === '/fermentation' ? 'active' : ''}>
            FERMENTATION / 发酵区
          </Link>
        </nav>
      </header>

      <div className="notice-bar">
        <Megaphone size={16} />
        <span>公告</span>
        <p>
          构石页与源站{' '}
          <a href="https://shitspace.xyz/realshit" target="_blank" rel="noreferrer">
            shitspace.xyz/realshit
          </a>{' '}
          同源；镜像列表为 <code className="notice-bar__code">GET /api/realshit</code>
          （字段对齐源站 <code className="notice-bar__code">/api/articles?tag=hardcore</code>
          ）。正文走本地 PDF 页图；可点「源站」对照。
        </p>
      </div>

      <main className="content">
        <div className="breadcrumb">Home &gt; Real Shit / 构石</div>

        <section className="realshit-hero" aria-labelledby="realshit-heading">
          <div className="realshit-hero__intro">
            <p className="realshit-hero__kicker">COLUMN / 栏目</p>
            <h1 id="realshit-heading">REAL SHIT</h1>
            <p className="realshit-hero__zh">构石</p>
            <p className="realshit-hero__lead">
              列表由后端 <code>GET /api/realshit</code> 提供，语义等同源站严谨论证（
              <code>tag=hardcore</code>），按通过时间倒序、每页 10 条。点击标题本地阅图；双列发酵区请前往{' '}
              <Link to="/fermentation">FERMENTATION / 发酵区</Link>。
            </p>
            <div className="hero-chips">
              <span className="pill realshit-pill">Truth Fades, S.H.*.T Lasts.</span>
              <span className="pill">{TAG_LABEL}</span>
              <span className="pill">库内严谨论证：{meta.total} 篇</span>
            </div>
          </div>
          <aside className="realshit-hero__aside">
            <strong>READING DESK / 阅读台</strong>
            <p className="realshit-hero__aside-meta">
              不在此页提供「欢乐鉴语」切换，与源站构石一致。若本地篇数少于源站，多为同步时间窗内尚未抓取；可点「立即同步」或调大后端抓取窗口。
            </p>
            <div className="realshit-hero__clock">
              <span>时间</span>
              <strong>{formatClock(clock)}</strong>
            </div>
            <p className="realshit-hero__sync">
              <Clock3 size={14} aria-hidden />
              上次索引 {formatDateTime(stats?.overview?.latest_crawl_at)}
            </p>
          </aside>
        </section>

        <section className="workspace workspace--realshit">
          <aside className="control-panel">
            <div className="control-panel__box">
              <div className="control-panel__title">
                <Sparkles size={16} />
                <span>构石 · 检索与同步</span>
              </div>
              <p className="realshit-panel__hint">
                数据来自 <code>GET /api/realshit</code>，与{' '}
                <a href="https://shitspace.xyz/realshit" target="_blank" rel="noreferrer">
                  源站构石
                </a>{' '}
                列表语义一致（严谨论证）。
              </p>
              <label className="search-box">
                <Search size={16} />
                <input
                  type="text"
                  value={filters.search}
                  placeholder="搜索标题 / 作者"
                  onChange={(event) => {
                    setPage(1)
                    setFilters((current) => ({ ...current, search: event.target.value }))
                  }}
                />
              </label>
              <button type="button" className="sync-button" onClick={syncArticles} disabled={syncing}>
                <RefreshCcw size={16} className={syncing ? 'spinning' : ''} />
                <span>{syncing ? '同步中' : '立即同步'}</span>
              </button>
            </div>

            <div className="control-panel__box muted">
              <span className="mini-label">说明</span>
              <p>
                文章抓取窗口：最近 {stats?.scheduler?.crawl_window_days || 5} 天。若列表为空，请先点「立即同步」或等待后台任务。
              </p>
            </div>
          </aside>

          <section className="listing-panel listing-panel--realshit">
            {loading ? (
              <div className="empty-state">正在读取本地镜像数据…</div>
            ) : articles.length === 0 ? (
              <div className="empty-state">
                时间窗内没有严谨论证稿件。请先同步，或到{' '}
                <Link to="/fermentation">发酵区</Link> 浏览全部标签。
              </div>
            ) : (
              <div className="realshit-feed" role="list">
                {articles.map((article) => (
                  <RealShitRow
                    key={article.id}
                    article={article}
                    onSelect={openArticle}
                    zoneLabel={zoneLabels[zoneKey(article)] || zoneKey(article) || '未分区'}
                    disciplineLabel={
                      disciplineLabels[article.discipline] || article.discipline || '未标注'
                    }
                  />
                ))}
              </div>
            )}

            <section className="pager">
              <button
                type="button"
                className="pager-button"
                onClick={() => setPage((current) => Math.max(1, current - 1))}
                disabled={page <= 1}
                aria-label="上一页"
              >
                <ChevronLeft size={18} />
              </button>
              <span>
                {meta.page} / {meta.total_pages || 1}
              </span>
              <button
                type="button"
                className="pager-button"
                onClick={() => setPage((current) => Math.min(meta.total_pages || 1, current + 1))}
                disabled={page >= (meta.total_pages || 1)}
                aria-label="下一页"
              >
                <ChevronRight size={18} />
              </button>
            </section>
          </section>
        </section>
      </main>

      <footer className="site-footer">
        <div className="site-footer__brand">
          <div className="footer-logo">▲ S.H.*.T SPACE</div>
          <p className="site-footer__eyebrow">SCIENCES · HUMANITIES · INFORMATION · TECHNOLOGY</p>
          <p>没有头衔通行证，没有权威裁决席。观点先于身份，发酵权属于所有人。</p>
        </div>
        <div className="site-footer__columns">
          <div>
            <h2>NAVIGATE / 导航</h2>
            <Link to="/">Home / 首页</Link>
            <Link to="/content/news">News / 新闻</Link>
            <Link to="/content/questions">Petri Dish / 培养皿</Link>
            <Link to="/realshit">Real Shit / 构石</Link>
            <Link to="/fermentation">Fermentation / 发酵区</Link>
          </div>
          <div>
            <h2>SOURCE / 源站</h2>
            <a href="https://shitspace.xyz" target="_blank" rel="noreferrer">
              shitspace.xyz
            </a>
            <a href="https://shitspace.xyz/realshit" target="_blank" rel="noreferrer">
              shitspace.xyz/realshit
            </a>
          </div>
        </div>
      </footer>

      <ArticleDetailModal article={selectedArticle} onClose={() => setSelectedArticle(null)} />
    </div>
  )
}
