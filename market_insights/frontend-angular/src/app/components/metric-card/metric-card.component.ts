import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-metric-card',
  standalone: true,
  template: `
  <div class="card kpi">
    <div class="label">{{ label }}</div>
    <div class="value">{{ value }}</div>
    <div class="muted" *ngIf="hint">{{ hint }}</div>
  </div>
  `,
})
export class MetricCardComponent {
  @Input() label = '';
  @Input() value: string | number = '';
  @Input() hint = '';
}
