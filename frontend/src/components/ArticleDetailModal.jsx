import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Download, FileImage, MessageCircle, ThumbsUp, X } from 'lucide-react'

function useImagePreloader() {
  const [loadedImages, setLoadedImages] = useState(new Set())
  const [failedImages, setFailedImages] = useState(new Set())

  const preloadImage = useCallback(
    (src) => {
      if (!src || loadedImages.has(src) || failedImages.has(src)) {
        return Promise.resolve()
      }

      return new Promise((resolve, reject) => {
        const img = new Image()
        img.onload = () => {
          setLoadedImages((prev) => new Set([...prev, src]))
          resolve(src)
        }
        img.onerror = () => {
          setFailedImages((prev) => new Set([...prev, src]))
          reject(src)
        }
        img.src = src
      })
    },
    [loadedImages, failedImages],
  )

  const preloadBatch = useCallback(
    async (sources, batchSize = 3) => {
      const validSources = sources.filter(
        (src) => src && !loadedImages.has(src) && !failedImages.has(src),
      )

      for (let i = 0; i < validSources.length; i += batchSize) {
        const batch = validSources.slice(i, i + batchSize)
        await Promise.allSettled(batch.map((src) => preloadImage(src)))
      }
    },
    [loadedImages, failedImages, preloadImage],
  )

  return { preloadBatch }
}

function ProgressiveImage({
  previewUrl,
  highResUrl,
  alt,
  index,
  onPreviewLoad,
  onHighResLoad,
  isPreviewLoaded,
  isHighResLoaded,
}) {
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
      { rootMargin: '100px' },
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
  latrine: '发酵区',
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

export function ArticleDetailModal({ article, onClose }) {
  const galleryRef = useRef(null)
  const { preloadBatch } = useImagePreloader()
  const [imageLoaded, setImageLoaded] = useState({})
  const [highResLoaded, setHighResLoaded] = useState({})

  const selectedSummary = useMemo(() => {
    if (!article) return null
    return {
      author: article.author_name || '匿名作者',
      date: formatDate(article.approved_at || article.created_at),
      discipline:
        disciplineLabels[article.discipline] || article.discipline || '未标注',
      zone: zoneLabels[article.zone] || article.zone || '未分区',
    }
  }, [article])

  useEffect(() => {
    if (!article?.pages?.length) return

    setImageLoaded({})
    setHighResLoaded({})

    const imagesToPreload = article.pages.slice(0, 3).flatMap((page) => {
      const previewUrl =
        page.page_number === 1
          ? article.cover_image_url?.replace('scale=0.9', 'scale=0.4')
          : page.image_url.replace('scale=1.8', 'scale=0.4')
      return [previewUrl, page.image_url]
    }).filter(Boolean)

    const t = window.setTimeout(() => {
      preloadBatch(imagesToPreload, 2)
    }, 100)
    return () => window.clearTimeout(t)
  }, [article, preloadBatch])

  if (!article) return null

  return (
    <section className="modal-backdrop" onClick={onClose}>
      <article className="article-modal" onClick={(event) => event.stopPropagation()}>
        <div className="article-modal__header">
          <div>
            <span className="modal-eyebrow">
              <FileImage size={14} />
              高清页图预览
            </span>
            <h2>{article.title}</h2>
          </div>
          <button type="button" className="icon-button" aria-label="关闭" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="article-modal__meta">
          <span>{selectedSummary?.author}</span>
          <span>{selectedSummary?.discipline}</span>
          <span>{selectedSummary?.zone}</span>
          <span>{selectedSummary?.date}</span>
          <span>{article.page_count || 0} 页</span>
        </div>

        <div className="article-modal__toolbar">
          <p>预览图由后端实时渲染，不在本地长期保存整套 PNG。</p>
          {article.download_url ? (
            <a href={article.download_url} target="_blank" rel="noreferrer" className="source-link">
              <Download size={16} />
              下载拼接后的 PDF
            </a>
          ) : null}
        </div>

        <div className="article-modal__gallery" ref={galleryRef}>
          {article.pages?.map((pageImage, index) => {
            const pageKey = `${article.id}-${pageImage.page_number}`
            const isPreviewLoaded = imageLoaded[pageKey]
            const isHighResLoaded = highResLoaded[pageKey]
            const previewUrl =
              pageImage.page_number === 1
                ? article.cover_image_url?.replace('scale=0.9', 'scale=0.4')
                : pageImage.image_url.replace('scale=1.8', 'scale=0.4')

            return (
              <figure key={pageImage.page_number} className="page-image-card">
                <ProgressiveImage
                  previewUrl={previewUrl}
                  highResUrl={pageImage.image_url}
                  alt={`第 ${pageImage.page_number} 页`}
                  index={index}
                  isPreviewLoaded={isPreviewLoaded}
                  isHighResLoaded={isHighResLoaded}
                  onPreviewLoad={() =>
                    setImageLoaded((prev) => ({ ...prev, [pageKey]: true }))
                  }
                  onHighResLoad={() =>
                    setHighResLoaded((prev) => ({ ...prev, [pageKey]: true }))
                  }
                />
                <figcaption>第 {pageImage.page_number} 页</figcaption>
              </figure>
            )
          })}
        </div>

        {article.comments && article.comments.length > 0 && (
          <div className="article-modal__comments">
            <h3 className="comments-title">
              <MessageCircle size={18} />
              评论 ({article.comments.length})
            </h3>
            <div className="comments-list">
              {article.comments.map((comment) => (
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
                    <span className="comment-date">{formatDateTime(comment.created_at)}</span>
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
  )
}
