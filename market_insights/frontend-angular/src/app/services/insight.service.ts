import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Injectable({ providedIn: 'root' })
export class InsightService {

  constructor(private http: HttpClient) {}

  getInsight(ticker: string) {
    return this.http.get(`/api/insights/${ticker}`);
  }

  getFairValue(ticker: string) {
    return this.http.get(`/api/fair-value/${ticker}`);
  }

  getSources(ticker: string) {
    return this.http.get(`/api/rag/sources/${ticker}`);
  }
}
