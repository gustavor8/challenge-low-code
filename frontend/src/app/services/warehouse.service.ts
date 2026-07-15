import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface Load {
  id: number;
  sku: string;
  name?: string;
  weight: number;
  is_imo: boolean;
  allocated_at: string;
}

export interface Slot {
  id: number;
  aisle: number;
  column: number;
  level: number;
  is_occupied: boolean;
  is_imo_restricted: boolean;
  load?: Load;
}

export interface OccupancyStats {
  total_slots: number;
  occupied_slots: number;
  occupancy_rate: number;
  imo_slots: number;
  occupied_imo_slots: number;
  limit_height: number;
}

@Injectable({
  providedIn: 'root'
})
export class WarehouseService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = environment.apiUrl;

  getWarehouseState(): Observable<Slot[]> {
    return this.http.get<Slot[]>(`${this.apiUrl}/warehouse/state`);
  }

  getOccupancyStats(): Observable<OccupancyStats> {
    return this.http.get<OccupancyStats>(`${this.apiUrl}/warehouse/occupancy`);
  }

  suggestAllocation(payload: { sku: string; weight: number; is_imo: boolean }): Observable<{
    slot_id: number;
    aisle: number;
    column: number;
    level: number;
    message: string;
  }> {
    return this.http.post<{
      slot_id: number;
      aisle: number;
      column: number;
      level: number;
      message: string;
    }>(`${this.apiUrl}/allocation/suggest`, payload);
  }

  confirmAllocation(payload: {
    slot_id: number;
    sku: string;
    name?: string;
    weight: number;
    is_imo: boolean;
  }): Observable<Slot> {
    return this.http.post<Slot>(`${this.apiUrl}/allocation/confirm`, payload);
  }

  unloadSlot(slotId: number): Observable<Slot> {
    return this.http.post<Slot>(`${this.apiUrl}/allocation/unload?slot_id=${slotId}`, {});
  }

  resetWarehouse(): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${this.apiUrl}/warehouse/reset`, {});
  }
}
