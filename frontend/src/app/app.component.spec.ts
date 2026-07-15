import { TestBed } from '@angular/core/testing';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { AppComponent } from './app.component';
import { WarehouseService } from './services/warehouse.service';
import { of } from 'rxjs';

describe('AppComponent', () => {
  let warehouseServiceSpy: jasmine.SpyObj<WarehouseService>;

  beforeEach(async () => {
    const spy = jasmine.createSpyObj('WarehouseService', ['getWarehouseState', 'getOccupancyStats']);
    spy.getWarehouseState.and.returnValue(of([]));
    spy.getOccupancyStats.and.returnValue(of({
      total_slots: 140,
      occupied_slots: 0,
      occupancy_rate: 0,
      imo_slots: 6,
      occupied_imo_slots: 0,
      limit_height: 4
    }));

    await TestBed.configureTestingModule({
      imports: [
        AppComponent,
        MatSnackBarModule,
        NoopAnimationsModule
      ],
      providers: [
        { provide: WarehouseService, useValue: spy },
        provideHttpClient(),
        provideHttpClientTesting()
      ]
    }).compileComponents();

    warehouseServiceSpy = TestBed.inject(WarehouseService) as jasmine.SpyObj<WarehouseService>;
  });

  it('deve criar o componente', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it('deve inicializar os signals com dados do service', () => {
    const fixture = TestBed.createComponent(AppComponent);
    fixture.detectChanges();
    const app = fixture.componentInstance;
    
    // Then
    expect(app.slots()).toEqual([]);
    expect(app.stats()).toEqual({
      total_slots: 140,
      occupied_slots: 0,
      occupancy_rate: 0,
      imo_slots: 6,
      occupied_imo_slots: 0,
      limit_height: 4
    });
    expect(warehouseServiceSpy.getWarehouseState).toHaveBeenCalled();
    expect(warehouseServiceSpy.getOccupancyStats).toHaveBeenCalled();
  });
});
