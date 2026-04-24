import { useEffect, useState, useRef } from 'react'
import { X, ThumbsUp, MessageCircle, Clock, User } from 'lucide-react'

function formatDateTime(value) {
  if (!value) return '未知时间'
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

export function ContentModal({ item, onClose, type }) {
  const [loading, setLoading] = useState(true)
  const [detail, setDetail] = useState(null)
  const modalRef = useRef(null)

  useEffect(() => {
    async function loadDetail() {
      setLoading(true)
      try {
        const response = await fetch(`/api/content/${type}/${item.id}`)
        const payload = await response.json()
        setDetail(payload.data)
      } catch (error) {
        console.error('Failed to load content detail:', error)
        setDetail(item)
      } finally {
        setLoading(false)
      }
    }

    if (item) {
      loadDetail()
    }
  }, [item, type])

  useEffect(() => {
    function handleEscape(e) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [onClose])

  const data = detail || item

  const typeLabels = {
    news: '新闻动态',
    questions: '培养皿问答',
    realshit: '稿石投稿',
  }

  return (
    <section className="modal-backdrop" onClick={onClose}>
      <article
        ref={modalRef}
        className="content-modal"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="content-modal__header">
          <div>
            <span className="content-modal__type">{typeLabels[type]}</span>
            <h2>{data.title}</h2>
          </div>
          <button type="button" className="icon-button" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="content-modal__meta">
          <div className="content-modal__author">
            {data.author?.avatar ? (
              <img src={data.author.avatar} alt={data.author.name} />
            ) : (
              <div className="content-modal__avatar-placeholder">
                <User size={16} />
              </div>
            )}
            <span>{data.author?.name || '匿名用户'}</span>
          </div>
          <span className="content-modal__date">
            <Clock size={14} />
            {formatDateTime(data.created_at)}
          </span>
          {data.tag && <span className="content-modal__tag">{data.tag}</span>}
        </div>

        <div className="content-modal__body">
          {loading ? (
            <div className="content-modal__loading">
              <div className="loading-spinner" />
              <span>加载中...</span>
            </div>
          ) : (
            <div
              className="content-modal__content"
              dangerouslySetInnerHTML={{ __html: data.content?.replace(/\n/g, '<br/>') }}
            />
          )}
        </div>

        {data.comments && data.comments.length > 0 && (
          <div className="content-modal__comments">
            <h3>
              <MessageCircle size={18} />
              评论 ({data.comments.length})
            </h3>
            <div className="comments-list">
              {data.comments.map((comment) => (
                <div key={comment.id} className="comment-item">
                  <div className="comment-header">
                    <div className="comment-user">
                      {comment.user?.avatar_url ? (
                        <img
                          src={comment.user.avatar_url}
                          alt={comment.user.display_name}
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
  )
}
