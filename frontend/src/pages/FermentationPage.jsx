import { useEffect, useMemo, useState, useCallback, useRef } from 'react'
import {
  ChevronLeft,
  ChevronRight,
  Clock3,
  Download,
  FileImage,
  Megaphone,
  Menu,
  MessageCircle,
  RefreshCcw,
  Search,
  Sparkles,
  ThumbsUp,
  X,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import '../App.css'

// 自定义 Hook：图片预加载
function useImagePreloader() {
  const [loadedImages, setLoadedImages] = useState(new Set())
  const [failedImages, setFailedImages] = useState(new Set())

  const preloadImage = useCallback((src) => {
    if (!src || loadedImages.has(src) || failedImages.has(src)) {
      return Promise.resolve()
    }

    return new Promise((resolve, reject) => {
      const img = new Image()
      img.onload = () => {
        setLoadedImages(prev => new Set([...prev, src]))
        resolve(src)
      }
      img.onerror = () => {
        setFailedImages(prev => new Set([...prev, src]))
        reject(src)
      }
      img.src = src
    })
  }, [loadedImages, failedImages])

  const preloadBatch = useCallback(async (sources, batchSize = 3) => {
    const validSources = sources.filter(src => src && !loadedImages.has(src) && !failedImages.has(src))

    for (let i = 0; i < validSources.length; i += batchSize) {
      const batch = validSources.slice(i, i + batchSize)
      await Promise.allSettled(batch.map(src => preloadImage(src)))
    }
  }, [loadedImages, failedImages, preloadImage])

  return { preloadImage, preloadBatch, loadedImages, failedImages }
}

// 渐进式图片加载组件
function ProgressiveImage({ previewUrl, highResUrl, alt, index, onPreviewLoad, onHighResLoad, isPreviewLoaded, isHighResLoaded }) {
  const [isInView, setIsInView] = useState(index < 3)
  const [shouldLoadHighRes, setShouldLoadHighRes] = useState(false)
  const wrapperRef = useRef(null)

  useEffect(() => {
    if (index < 3) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true)
          observer.disconnect()
        }
      },
      { rootMargin: '100px' }
    )

    if (wrapperRef.current) {
      observer.observe(wrapperRef.current)
    }

    return () => observer.disconnect()
  }, [index])

  useEffect(() => {
    if (isPreviewLoaded && !isHighResLoaded) {
      const timer = setTimeout(() => {
        setShouldLoadHighRes(true)
      }, 200)
      return () => clearTimeout(timer)
    }
  }, [isPreviewLoaded, isHighResLoaded])

  return (
    <div ref={wrapperRef} className="page-image-wrapper">
      {!isPreviewLoaded && !isHighResLoaded && (
        <div className="page-image-skeleton">
          <div className="skeleton-shimmer" />
          <div className="page-image-loading">
            <FileImage size={28} />
            <span>加载中...</span>
          </div>
        </div>
      )}

      {isInView && !isHighResLoaded && (
        <img
          src={previewUrl}
          alt={`${alt} 预览`}
          className={`page-image-preview ${isPreviewLoaded ? 'fade-in' : 'hidden'}`}
          onLoad={onPreviewLoad}
        />
      )}

      {(isInView && (shouldLoadHighRes || isPreviewLoaded)) && (
        <img
          src={highResUrl}
          alt={alt}
          className={`page-image-highres ${isHighResLoaded ? 'fade-in' : 'hidden'}`}
          onLoad={onHighResLoad}
        />
      )}
    </div>
  )
}

const zoneOptions = [
  { value: '', label: '全部专区' },
  { value: 'latrine', label: '发酵区' },
  { value: 'published', label: '已发表' },
]

const tagOptions = [
  { value: '', label: '全部标签' },
  { value: 'meme', label: '欢乐鉴语' },
  { value: 'hardcore', label: '严谨论证' },
]

const disciplineLabels = {
  interdisciplinary: '交叉学科',
  social: '社会学',
  management: '管理学',
  economics: '经济学',
  law: '法学',
  literature: '文学',
  engineering: '工程学',
}

const zoneLabels = {
  latrine: 'Fermentation / 发酵区',
  published: 'Published / 已发表',
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

function scoreLabel(score) {
  if (score >= 4.5) return '高分'
  if (score >= 3.5) return '稳定'
  if (score > 0) return '待观察'
  return '未评分'
}

function ArticleCard({ article, onSelect }) {
  const score = Number(article.avg_score || 0)
  const scorePercent = Math.max(0, Math.min((score / 5) * 100, 100))

  return (
    <article className="article-card">
      <button type="button" className="article-card__button" onClick={() => onSelect(article.id)}>
        <div className="article-card__visual">
          {article.cover_image_url ? (
            <img src={article.cover_image_url} alt="" />
          ) : (
            <div className="article-card__visual-fallback">
              <FileImage size={32} />
            </div>
          )}
        </div>

        <div className="article-card__content">
          <div className="article-card__top">
            <div className="article-card__headline">
              <span className="article-card__eyebrow">
                {tagOptions.find((item) => item.value === article.tag)?.label || article.tag || '未分类'}
              </span>
              <h3>{article.title}</h3>
            </div>
            <div className="article-card__score">
              <span className="score-track">
                <span className="score-track__fill" style={{ width: `${scorePercent}%` }} />
              </span>
              <strong>{score.toFixed(1)}</strong>
              <span>{scoreLabel(score)}</span>
            </div>
          </div>

          <div className="article-card__meta">
            <span>{article.author_name || '匿名作者'}</span>
            <span>{disciplineLabels[article.discipline] || article.discipline || '未标注'}</span>
            <span>{formatDate(article.approved_at || article.created_at)}</span>
            <span>{article.page_count || 0} 页</span>
          </div>
        </div>
      </button>

      <div className="article-card__footer">
        <span>
          <MessageCircle size={14} />
          {article.comment_count || 0} 评论
        </span>
        {article.download_url ? (
          <a href={article.download_url} className="download-link" target="_blank" rel="noreferrer">
            <Download size={14} />
            下载 PDF
          </a>
        ) : (
          <span className="download-link disabled">
            <Download size={14} />
            PDF 未就绪
          </span>
        )}
      </div>
    </article>
  )
}

export function FermentationPage() {
  const [filters, setFilters] = useState({
    zone: 'latrine',
    tag: '',
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
  const { preloadBatch } = useImagePreloader()
  const galleryRef = useRef(null)

  const [imageLoaded, setImageLoaded] = useState({})
  const [highResLoaded, setHighResLoaded] = useState({})

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

      if (filters.zone) query.set('zone', filters.zone)
      if (filters.tag) query.set('tag', filters.tag)
      if (filters.search.trim()) query.set('search', filters.search.trim())

      const [articlesResponse, statsResponse] = await Promise.all([
        fetch(`/api/articles?${query.toString()}`, { signal: controller.signal }),
        fetch('/api/stats', { signal: controller.signal }),
      ])

      const articlesPayload = await articlesResponse.json()
      const statsPayload = await statsResponse.json()

      setArticles(articlesPayload.data || [])
      setMeta(articlesPayload.meta || { page: 1, total_pages: 0, total: 0 })
      setStats(statsPayload.data || null)
      setLoading(false)
    }

    loadData().catch((error) => {
      if (error.name !== 'AbortError') setLoading(false)
    })

    return () => controller.abort()
  }, [filters, page])

  async function openArticle(articleId) {
    setImageLoaded({})
    setHighResLoaded({})
    const response = await fetch(`/api/articles/${articleId}`)
    const payload = await response.json()
    const article = payload.data
    setSelectedArticle(article)

    if (article?.pages?.length > 0) {
      const imagesToPreload = article.pages.slice(0, 3).flatMap((page) => {
        const previewUrl = page.page_number === 1
          ? article.cover_image_url?.replace('scale=0.9', 'scale=0.4')
          : page.image_url.replace('scale=1.8', 'scale=0.4')
        return [previewUrl, page.image_url]
      }).filter(Boolean)

      setTimeout(() => {
        preloadBatch(imagesToPreload, 2)
      }, 100)
    }
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

  const heading = zoneLabels[filters.zone] || 'S.H.*.T Space / 文章镜像'
  const selectedSummary = useMemo(() => {
    if (!selectedArticle) return null
    return {
      author: selectedArticle.author_name || '匿名作者',
      date: formatDate(selectedArticle.approved_at || selectedArticle.created_at),
      discipline:
        disciplineLabels[selectedArticle.discipline] || selectedArticle.discipline || '未标注',
      zone: zoneLabels[selectedArticle.zone] || selectedArticle.zone || '未分区',
    }
  }, [selectedArticle])

  return (
    <div className="page-shell">
      <header className="topbar">
        <div className="topbar__inner">
          <button type="button" className="icon-link">
            <Menu size={18} />
            <span>MENU</span>
          </button>
          <Link to="/" className="brandmark">SH*T</Link>
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
          <Link to="/">HOME</Link>
          <Link to="/content/news">NEWS / 新闻</Link>
          <Link to="/content/questions">PETRI DISH / 培养皿</Link>
          <Link to="/" className="active">FERMENTATION / 发酵区</Link>
        </nav>
      </header>

      <div className="notice-bar">
        <Megaphone size={16} />
        <span>公告</span>
        <p>启动后会同步最近 5 天的文章，并在每次同步时清理超出时效的 PDF。</p>
      </div>

      <main className="content">
        <div className="breadcrumb">Home &gt; Fermentation / 发酵区</div>

        <section className="hero-section">
          <div className="hero-copy">
            <h1>{heading}</h1>
            <p>
              站点以源 PDF 为基底生成高分辨率页图预览，并提供重新拼接后的 PDF 下载。
            </p>
            <div className="hero-chips">
              <span className="pill">当前筛选：{tagOptions.find((item) => item.value === filters.tag)?.label || '全部标签'}</span>
              <span className="pill">抓取范围：最近 {stats?.scheduler?.crawl_window_days || 5} 天</span>
              <span className="pill">库内文章：{meta.total}</span>
            </div>
          </div>

          <div className="hero-clock">
            <span>公网时间</span>
            <strong>{formatClock(clock)}</strong>
            <div className="hero-clock__meta">
              <Clock3 size={14} />
              <span>{formatDateTime(stats?.overview?.latest_crawl_at)}</span>
            </div>
          </div>
        </section>

        <section className="dashboard-strip">
          <div className="dashboard-card">
            <span>文章总数</span>
            <strong>{stats?.overview?.article_count ?? 0}</strong>
            <p>已完成索引的文章数量</p>
          </div>
          <div className="dashboard-card">
            <span>页图总量</span>
            <strong>{stats?.overview?.page_count ?? 0}</strong>
            <p>按需渲染的总页数参考值</p>
          </div>
          <div className="dashboard-card">
            <span>PDF 可下载</span>
            <strong>{stats?.overview?.pdf_ready_count ?? 0}</strong>
            <p>已完成拼接并可直接下载</p>
          </div>
          <div className="dashboard-card accent">
            <span>同步状态</span>
            <strong>{stats?.scheduler?.running ? '同步中' : '空闲'}</strong>
            <p>
              上次完成于 {formatDateTime(stats?.scheduler?.last_finished_at || stats?.overview?.latest_crawl_at)}
            </p>
          </div>
        </section>

        <section className="workspace">
          <aside className="control-panel">
            <div className="control-panel__box">
              <div className="control-panel__title">
                <Sparkles size={16} />
                <span>筛选与同步</span>
              </div>
              <div className="filter-group">
                {zoneOptions.map((option) => (
                  <button
                    key={option.value || 'all-zone'}
                    type="button"
                    className={filters.zone === option.value ? 'filter-chip active' : 'filter-chip'}
                    onClick={() => {
                      setPage(1)
                      setFilters((current) => ({ ...current, zone: option.value }))
                    }}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
              <div className="filter-group">
                {tagOptions.map((option) => (
                  <button
                    key={option.value || 'all-tag'}
                    type="button"
                    className={filters.tag === option.value ? 'filter-chip alt active' : 'filter-chip alt'}
                    onClick={() => {
                      setPage(1)
                      setFilters((current) => ({ ...current, tag: option.value }))
                    }}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
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
              <p>当前并不是抓网页预览缩略图，而是从源 PDF 重新高倍率渲染。原站未暴露整页原始图片资源时，这是更清晰也更稳定的方式。</p>
            </div>
          </aside>

          <section className="listing-panel">
            {loading ? (
              <div className="empty-state">正在读取本地镜像数据…</div>
            ) : articles.length === 0 ? (
              <div className="empty-state">当前筛选条件下没有文章。</div>
            ) : (
              <div className="articles-grid">
                {articles.map((article) => (
                  <ArticleCard key={article.id} article={article} onSelect={openArticle} />
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
          <div className="footer-logo">S.H.*.T SPACE</div>
          <p>Sciences · Humanities · Information · Technology</p>
          <p>没有头衔通行证，没有权威裁决席。观点先于身份，发酵权属于所有人。</p>
        </div>
        <div className="site-footer__columns">
          <div>
            <h2>GUIDELINES / 指南</h2>
            <a href="/">Acceptance Criteria</a>
            <a href="/">Submission Restrictions</a>
          </div>
          <div>
            <h2>ABOUT / 关于</h2>
            <a href="/">About S.H.*.T</a>
            <a href="/">Contact</a>
            <a href="/">Feedback</a>
          </div>
        </div>
      </footer>

      {selectedArticle ? (
        <section className="modal-backdrop" onClick={() => setSelectedArticle(null)}>
          <article className="article-modal" onClick={(event) => event.stopPropagation()}>
            <div className="article-modal__header">
              <div>
                <span className="modal-eyebrow">
                  <FileImage size={14} />
                  高清页图预览
                </span>
                <h2>{selectedArticle.title}</h2>
              </div>
              <button
                type="button"
                className="icon-button"
                aria-label="关闭"
                onClick={() => setSelectedArticle(null)}
              >
                <X size={18} />
              </button>
            </div>

            <div className="article-modal__meta">
              <span>{selectedSummary?.author}</span>
              <span>{selectedSummary?.discipline}</span>
              <span>{selectedSummary?.zone}</span>
              <span>{selectedSummary?.date}</span>
              <span>{selectedArticle.page_count || 0} 页</span>
            </div>

            <div className="article-modal__toolbar">
              <p>预览图由后端实时渲染，不在本地长期保存整套 PNG。</p>
              {selectedArticle.download_url ? (
                <a href={selectedArticle.download_url} target="_blank" rel="noreferrer" className="source-link">
                  <Download size={16} />
                  下载拼接后的 PDF
                </a>
              ) : null}
            </div>

            <div className="article-modal__gallery" ref={galleryRef}>
              {selectedArticle.pages?.map((pageImage, index) => {
                const pageKey = `${selectedArticle.id}-${pageImage.page_number}`
                const isPreviewLoaded = imageLoaded[pageKey]
                const isHighResLoaded = highResLoaded[pageKey]
                const previewUrl = pageImage.page_number === 1
                  ? selectedArticle.cover_image_url?.replace('scale=0.9', 'scale=0.4')
                  : pageImage.image_url.replace('scale=1.8', 'scale=0.4')

                return (
                  <figure key={pageImage.page_number} className="page-image-card">
                    <ProgressiveImage
                      previewUrl={previewUrl}
                      highResUrl={pageImage.image_url}
                      alt={`第 ${pageImage.page_number} 页`}
                      pageKey={pageKey}
                      index={index}
                      isPreviewLoaded={isPreviewLoaded}
                      isHighResLoaded={isHighResLoaded}
                      onPreviewLoad={() => setImageLoaded(prev => ({ ...prev, [pageKey]: true }))}
                      onHighResLoad={() => setHighResLoaded(prev => ({ ...prev, [pageKey]: true }))}
                    />
                    <figcaption>第 {pageImage.page_number} 页</figcaption>
                  </figure>
                )
              })}
            </div>

            {selectedArticle.comments && selectedArticle.comments.length > 0 && (
              <div className="article-modal__comments">
                <h3 className="comments-title">
                  <MessageCircle size={18} />
                  评论 ({selectedArticle.comments.length})
                </h3>
                <div className="comments-list">
                  {selectedArticle.comments.map((comment) => (
                    <div key={comment.id} className="comment-item">
                      <div className="comment-header">
                        <div className="comment-user">
                          {comment.user?.avatar_url ? (
                            <img
                              src={comment.user.avatar_url}
                              alt={comment.user.display_name || '用户'}
                              className="comment-avatar"
                            />
                          ) : (
                            <div className="comment-avatar-placeholder">
                              {(comment.user?.display_name || '匿').charAt(0)}
                            </div>
                          )}
                          <span className="comment-username">
                            {comment.user?.display_name || '匿名用户'}
                          </span>
                        </div>
                        <span className="comment-date">
                          {formatDateTime(comment.created_at)}
                        </span>
                      </div>
                      <p className="comment-content">{comment.content}</p>
                      <div className="comment-footer">
                        <span className="comment-likes">
                          <ThumbsUp size={14} />
                          {comment.like_count || 0}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </article>
        </section>
      ) : null}
    </div>
  )
}
