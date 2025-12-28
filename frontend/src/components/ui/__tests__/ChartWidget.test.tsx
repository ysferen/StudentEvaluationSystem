import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ChartWidget } from '../ChartWidget'

describe('ChartWidget Component', () => {
  const mockSeries = [
    {
      name: 'Series 1',
      data: [30, 40, 35, 50, 49, 60, 70, 91, 125],
    },
  ]

  const mockOptions = {
    xaxis: {
      categories: ['1991', '1992', '1993', '1994', '1995', '1996', '1997', '1998', '1999'],
    },
  }

  it('renders chart title', () => {
    render(<ChartWidget title="Test Chart" type="line" series={mockSeries} />)
    expect(screen.getByText('Test Chart')).toBeInTheDocument()
  })

  it('renders subtitle when provided', () => {
    render(
      <ChartWidget title="Test Chart" subtitle="Test Subtitle" type="line" series={mockSeries} />
    )
    expect(screen.getByText('Test Subtitle')).toBeInTheDocument()
  })

  it('does not render subtitle when not provided', () => {
    render(<ChartWidget title="Test Chart" type="line" series={mockSeries} />)
    expect(screen.queryByTestId('chart-subtitle')).not.toBeInTheDocument()
  })

  it('renders line chart', () => {
    const { container } = render(
      <ChartWidget title="Line Chart" type="line" series={mockSeries} options={mockOptions} />
    )
    expect(container.firstChild).toBeInTheDocument()
  })

  it('renders bar chart', () => {
    const { container } = render(
      <ChartWidget title="Bar Chart" type="bar" series={mockSeries} options={mockOptions} />
    )
    expect(container.firstChild).toBeInTheDocument()
  })

  it('renders area chart', () => {
    const { container } = render(
      <ChartWidget title="Area Chart" type="area" series={mockSeries} options={mockOptions} />
    )
    expect(container.firstChild).toBeInTheDocument()
  })

  it('renders radar chart', () => {
    const { container } = render(
      <ChartWidget title="Radar Chart" type="radar" series={mockSeries} options={mockOptions} />
    )
    expect(container.firstChild).toBeInTheDocument()
  })

  it('renders donut chart', () => {
    const donutSeries = [44, 55, 13, 33]
    const { container } = render(
      <ChartWidget title="Donut Chart" type="donut" series={donutSeries} />
    )
    expect(container.firstChild).toBeInTheDocument()
  })

  it('renders pie chart', () => {
    const pieSeries = [44, 55, 13, 33]
    const { container } = render(
      <ChartWidget title="Pie Chart" type="pie" series={pieSeries} />
    )
    expect(container.firstChild).toBeInTheDocument()
  })

  it('applies custom className', () => {
    const { container } = render(
      <ChartWidget
        title="Test Chart"
        type="line"
        series={mockSeries}
        className="custom-chart-class"
      />
    )
    const card = container.firstChild as HTMLElement
    expect(card.className).toContain('custom-chart-class')
  })

  it('uses default height when not specified', () => {
    const { container } = render(
      <ChartWidget title="Test Chart" type="line" series={mockSeries} />
    )
    expect(container.firstChild).toBeInTheDocument()
  })

  it('uses custom height when specified', () => {
    const { container } = render(
      <ChartWidget title="Test Chart" type="line" series={mockSeries} height={500} />
    )
    expect(container.firstChild).toBeInTheDocument()
  })

  it('merges custom options with default options', () => {
    const customOptions = {
      chart: {
        toolbar: {
          show: true,
        },
      },
      xaxis: {
        categories: ['A', 'B', 'C'],
      },
    }

    const { container } = render(
      <ChartWidget
        title="Test Chart"
        type="line"
        series={mockSeries}
        options={customOptions}
      />
    )
    expect(container.firstChild).toBeInTheDocument()
  })

  it('renders multiple series', () => {
    const multiSeries = [
      { name: 'Series 1', data: [30, 40, 35] },
      { name: 'Series 2', data: [20, 30, 25] },
    ]

    const { container } = render(
      <ChartWidget title="Multi Series Chart" type="line" series={multiSeries} />
    )
    expect(container.firstChild).toBeInTheDocument()
  })
})
