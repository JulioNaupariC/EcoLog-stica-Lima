import type { ReactNode } from 'react'
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
 * as a card (labels from data-label). Explicit ARIA roles keep the table
 * semantics when rows are displayed as blocks; nothing is rendered twice.
 */
export function DataTable<Row>({ columns, rows, rowKey, caption, label }: {
  columns: Column<Row>[]
  rows: Row[]
  rowKey: (row: Row) => string
  caption: string
  label: string
}) {
  return <div className="data-table-wrap" role="region" aria-label={label} tabIndex={0}>
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
          {columns.map(column => <td key={column.key} role="cell" data-label={column.header}
            className={cx(column.align === 'end' && 'is-end', column.primary && 'is-primary')}>
            {column.render(row)}
          </td>)}
        </tr>)}
      </tbody>
    </table>
  </div>
}
