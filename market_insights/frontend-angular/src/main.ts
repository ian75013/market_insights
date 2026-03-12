import { bootstrapApplication } from '@angular/platform-browser';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter, Routes } from '@angular/router';
import { AppComponent } from './app/app.component';
import { DashboardPageComponent } from './app/pages/dashboard/dashboard-page.component';

const routes: Routes = [
  { path: '', component: DashboardPageComponent },
];

bootstrapApplication(AppComponent, {
  providers: [provideHttpClient(), provideRouter(routes)],
}).catch((err) => console.error(err));
