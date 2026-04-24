import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Search, Menu, ChevronRight, Star, MessageCircle } from 'lucide-react'
import '../App.css'

function formatDate(value) {
  if (!value) return ''
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'short',
    day: 'numeric',
  }).format(new Date(value))
}

function StarRating({ score, count }) {
  const fullStars = Math.floor(score)
  const hasHalf = score % 1 >= 0.5
  
  return (
    <div className="star-rating">
      {[...Array(5)].map((_, i) => (
        <Star
          key={i}
          size={12}
          className={i < fullStars ? 'star-filled' : i === fullStars && hasHalf ? 'star-half' : 'star-empty'}
        />
      ))}
      <span className="rating-count">({count})</span>
    </div>
  )
}

export function HomePage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadData() {
      try {
        const response = await fetch('/api/homepage')
        const payload = await response.json()
        setData(payload.data)
      } catch (error) {
        console.error('Failed to load homepage data:', error)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  if (loading) {
    return <div className="page-shell"><div className="loading-container">加载中...</div></div>
  }

  const editorial = data?.editorial || {}
  const articles = data?.articles || []
  const news = data?.news || []
  // questions data is fetched but not displayed in current layout
  // const questions = data?.questions || []

  return (
    <div className="page-shell homepage">
      {/* Header */}
      <header className="topbar home-topbar">
        <div className="topbar__inner">
          <button type="button" className="icon-link">
            <Menu size={18} />
            <span>菜单</span>
          </button>
          <Link to="/" className="brandmark home-brand">
            <span className="brand-main">S.H.*.T</span>
            <span className="brand-sub">Sciences · Humanities · Information · Technology</span>
          </Link>
          <div className="topbar__actions">
            <button type="button" className="icon-button" aria-label="搜索">
              <Search size={18} />
            </button>
            <button type="button" className="login-button home-login">
              LOG IN / 登录
            </button>
          </div>
        </div>
        <nav className="navstrip home-nav">
          <Link to="/" className="active">HOME</Link>
          <Link to="/content/news">NEWS / 新闻</Link>
          <Link to="/content/questions">PETRI DISH / 培养皿</Link>
          <Link to="/fermentation">FERMENTATION / 发酵区</Link>
        </nav>
      </header>

      {/* Hero Section */}
      <section className="hero-banner">
        <div className="hero-logo">
          <div className="logo-icon">▲</div>
        </div>
        <h1 className="hero-quote">"Truth Fades, S.H.*.T Lasts."</h1>
        <p className="hero-subquote">"真理易逝，构石永恒。"</p>
      </section>

      {/* Main Content */}
      <main className="home-content">
        <div className="home-grid">
          {/* Editorial Section */}
          <section className="editorial-section">
            <div className="section-header">
              <h2>{editorial.subtitle || 'EDITORIAL / 社论'}</h2>
              <span className="section-date">VOL. 1, ISSUE 1</span>
            </div>
            <div className="editorial-content">
              <div className="editorial-image">
                <div className="placeholder-image">Editorial Feature</div>
              </div>
              <div className="editorial-text">
                <h3>{editorial.title || 'A Manifesto for Academic Decentralization'}</h3>
                <h4>{editorial.title_cn || '全民学术人宣言'}</h4>
                <div className="editorial-body">
                  {(editorial.content || '').split('\n\n').map((para, i) => (
                    <p key={i}>{para}</p>
                  ))}
                </div>
                <div className="editorial-actions">
                  <Link to="/" className="action-link primary">阅读完整版 →</Link>
                  <Link to="/" className="action-link">订阅邮件通知 →</Link>
                </div>
              </div>
            </div>
          </section>

          {/* Latest News Sidebar */}
          <aside className="news-sidebar">
            <div className="section-header">
              <h2>LATEST NEWS / 最新动态</h2>
            </div>
            <div className="news-list">
              {news.map((item) => (
                <article key={item.id} className="news-item">
                  <span className="news-date">{formatDate(item.created_at)}</span>
                  <h4>{item.title}</h4>
                  <p>{item.summary}</p>
                </article>
              ))}
            </div>
            <Link to="/content/news" className="more-link">
              MORE NEWS / 更多新闻 <ChevronRight size={14} />
            </Link>
            
            {/* Newsletter Box */}
            <div className="newsletter-box">
              <div className="newsletter-icon">▲</div>
              <h4>NEWSLETTER / 通讯</h4>
              <p>Subscribe to our newsletter for updates</p>
              <button className="subscribe-btn">SUBSCRIBE / 立即订阅</button>
            </div>
          </aside>
        </div>

        {/* Latest Research Section */}
        <section className="research-section">
          <div className="section-header">
            <h2>LATEST RESEARCH / 最新研究</h2>
            <span className="section-meta">APRIL 2024 • VOL. 1, ISSUE 1 • 发酵区</span>
          </div>
          <div className="research-list">
            {articles.map((article) => (
              <article key={article.id} className="research-item">
                <div className="research-main">
                  <h3>{article.title}</h3>
                  <div className="research-meta">
                    <span className="author">{article.author?.display_name || '匿名作者'}</span>
                    <span className="tag">{article.tag === 'meme' ? '欢乐鉴语' : article.tag === 'hardcore' ? '严谨论证' : article.tag}</span>
                    <span className="discipline">
                      {article.discipline === 'interdisciplinary' ? '交叉学科' : article.discipline}
                    </span>
                    <span className="comments"><MessageCircle size={12} /> {article.comment_count}</span>
                  </div>
                </div>
                <div className="research-rating">
                  <StarRating score={article.avg_score || 0} count={article.rating_count || 0} />
                </div>
              </article>
            ))}
          </div>
        </section>

        {/* Browse Archive */}
        <section className="browse-section">
          <h3>BROWSE ARCHIVE</h3>
          <div className="browse-filters">
            <select className="filter-select">
              <option>全部目录</option>
              <option>发酵区</option>
              <option>已发表</option>
            </select>
            <select className="filter-select">
              <option>SELECT MONTH</option>
            </select>
            <button className="filter-btn">GO →</button>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="home-footer">
        <div className="footer-content">
          <div className="footer-brand">
            <div className="footer-logo">▲ S.H.*.T SPACE</div>
            <p className="footer-tagline">SCIENCES · HUMANITIES · INFORMATION · TECHNOLOGY</p>
            <p className="footer-desc">没有头衔通行证，没有权威裁决席。观点先于身份，发酵权属于所有人。</p>
          </div>
          <div className="footer-links">
            <div className="footer-column">
              <h4>GUIDELINES / 指南</h4>
              <a href="/">Acceptance Criteria</a>
              <a href="/">Submission Restrictions</a>
            </div>
            <div className="footer-column">
              <h4>ABOUT / 关于</h4>
              <a href="/">About S.H.*.T</a>
              <a href="/">Contact</a>
              <a href="/">Feedback</a>
              <a href="/">System Status</a>
            </div>
          </div>
        </div>
        <div className="footer-bottom">
          <span>© 2024 S.H.*.T Space. All rights reserved.</span>
          <div className="footer-legal">
            <a href="/">PRIVACY POLICY / 隐私政策</a>
            <a href="/">TERMS OF SERVICE / 服务条款</a>
          </div>
        </div>
      </footer>
    </div>
  )
}
