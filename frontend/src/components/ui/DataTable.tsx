import { useEffect, useId, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { Button } from './Button'
import { cx } from './cx'

export interface Column<Row> {
  key: string
  header: string
  render: (row: Row) => ReactNode
  align?: 'start' | 'end'
  /** Shown as the card title on narrow screens. */
  primary?: boolean
}

/**
 * One semantic table for every width: on narrow screens CSS presents each row
 * as a card (labels from data-label). Explicit container roles keep the table
 * structure; cells retain their native td semantics. Nothing is rendered twice.
 */
export function DataTable<Row>({ columns, rows, rowKey, caption, label }: {
  columns: Column<Row>[]
  rows: Row[]
  rowKey: (row: Row) => string
  caption: string
  label: string
}) {
  const scrollId = useId()
  const scrollRef = useRef<HTMLDivElement>(null)
  const [overflowing, setOverflowing] = useState(false)

  useEffect(() => {
    const viewport = scrollRef.current
    if (!viewport) return
    const updateOverflow = () => setOverflowing(viewport.scrollWidth > viewport.clientWidth)
    const observer = new ResizeObserver(updateOverflow)
    observer.observe(viewport)
    if (viewport.firstElementChild) observer.observe(viewport.firstElementChild)
    return () => observer.disconnect()
  }, [])

  function scroll(direction: number) {
    const viewport = scrollRef.current
    if (viewport) viewport.scrollLeft += direction * viewport.clientWidth
  }

  // Native buttons provide keyboard scrolling without making a static region
  // interactive. Keep them enabled at either edge so focus stays on the button.
  return <div role="region" aria-label={label}>
    {overflowing ? <div className="form-actions">
      <Button variant="secondary" size="sm" aria-controls={scrollId} onClick={() => scroll(-1)}>
        Desplazar tabla a la izquierda
      </Button>
      <Button variant="secondary" size="sm" aria-controls={scrollId} onClick={() => scroll(1)}>
        Desplazar tabla a la derecha
      </Button>
    </div> : null}
    <div className="data-table-wrap" id={scrollId} ref={scrollRef}>
      <table className="data-table" role="table">
        <caption className="visually-hidden">{caption}</caption>
        <thead role="rowgroup">
          <tr role="row">
            {columns.map(column => <th key={column.key} scope="col" role="columnheader"
              className={cx(column.align === 'end' && 'is-end')}>{column.header}</th>)}
          </tr>
        </thead>
        <tbody role="rowgroup">
          {rows.map(row => <tr key={rowKey(row)} role="row">
            {columns.map(column => <td key={column.key} data-label={column.header}
              className={cx(column.align === 'end' && 'is-end', column.primary && 'is-primary')}>
              {column.render(row)}
            </td>)}
          </tr>)}
        </tbody>
      </table>
    </div>
  </div>
}
