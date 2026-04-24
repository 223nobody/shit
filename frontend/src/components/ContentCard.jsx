import { MessageCircle, ThumbsUp, Eye, Clock } from 'lucide-react'

function formatDate(value) {
  if (!value) return '未知时间'
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(value))
}

function formatNumber(num) {
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  return num.toString()
}

export function ContentCard({ item, onSelect, type }) {
  const typeLabels = {
    news: '新闻',
    questions: '问答',
    realshit: '稿石',
  }

  const typeColors = {
    news: '#3b82f6',
    questions: '#10b981',
    realshit: '#f59e0b',
  }

  return (
    <article className="content-card" onClick={() => onSelect(item)}>
      <div className="content-card__header">
        <span
          className="content-card__type"
          style={{ backgroundColor: `${typeColors[type]}20`, color: typeColors[type] }}
        >
          {typeLabels[type]}
        </span>
        {item.tag && <span className="content-card__tag">{item.tag}</span>}
      </div>

      <h3 className="content-card__title">{item.title}</h3>

      {item.content && (
        <p className="content-card__excerpt">
          {item.content.slice(0, 150)}{item.content.length > 150 ? '...' : ''}
        </p>
      )}

      <div className="content-card__footer">
        <div className="content-card__author">
          {item.author?.avatar ? (
            <img src={item.author.avatar} alt={item.author.name} className="content-card__avatar" />
          ) : (
            <div className="content-card__avatar-placeholder">
              {(item.author?.name || '匿').charAt(0)}
            </div>
          )}
          <span className="content-card__author-name">{item.author?.name || '匿名用户'}</span>
        </div>

        <div className="content-card__stats">
          <span className="content-card__stat">
            <Clock size={14} />
            {formatDate(item.created_at)}
          </span>
          {item.view_count > 0 && (
            <span className="content-card__stat">
              <Eye size={14} />
              {formatNumber(item.view_count)}
            </span>
          )}
          {item.like_count > 0 && (
            <span className="content-card__stat">
              <ThumbsUp size={14} />
              {formatNumber(item.like_count)}
            </span>
          )}
          {item.comment_count > 0 && (
            <span className="content-card__stat">
              <MessageCircle size={14} />
              {formatNumber(item.comment_count)}
            </span>
          )}
        </div>
      </div>
    </article>
  )
}
