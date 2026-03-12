import { Component } from '@angular/core';
import { InsightService } from '../../services/insight.service';

@Component({
  selector: 'app-insight',
  templateUrl: './insight.component.html'
})
export class InsightComponent {

  ticker = "AAPL";
  insight: any;

  constructor(private service: InsightService) {}

  loadInsight() {
    this.service.getInsight(this.ticker)
      .subscribe(data => this.insight = data);
  }
}
