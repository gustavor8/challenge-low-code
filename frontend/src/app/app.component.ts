import { Component, OnInit, signal, computed, inject, DestroyRef, ChangeDetectionStrategy } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, FormGroup, FormControl, Validators, ReactiveFormsModule } from '@angular/forms';
import { DatePipe } from '@angular/common';
import { finalize } from 'rxjs';

// Angular Material Imports
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';

import { WarehouseService, Slot, OccupancyStats } from './services/warehouse.service';
import { getErrorMessage } from './utils/forms/error-messages';

interface LoadForm {
  sku: FormControl<string>;
  name: FormControl<string>;
  weight: FormControl<number | null>;
  isImo: FormControl<boolean>;
}

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
  standalone: true,
  imports: [
    DatePipe,
    ReactiveFormsModule,
    MatToolbarModule,
    MatSidenavModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatSnackBarModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MatDividerModule,
    MatTooltipModule
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AppComponent implements OnInit {
  private readonly warehouseService = inject(WarehouseService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly fb = inject(FormBuilder);
  private readonly destroyRef = inject(DestroyRef);

  // App State Signals
  readonly slots = signal<Slot[]>([]);
  readonly stats = signal<OccupancyStats | null>(null);
  readonly isLoading = signal<boolean>(false);
  readonly activeHeightRule = signal<string>('auto');
  
  // Selection and Recommendations Signals
  readonly selectedSlot = signal<Slot | null>(null);
  readonly suggestedSlot = signal<Slot | null>(null);
  readonly suggestedMessage = signal<string | null>(null);

  // Grid Configuration Constants
  readonly aisles = [1, 2];
  readonly columns = Array.from({ length: 10 }, (_, i) => i + 1); // 1 to 10
  readonly levels = Array.from({ length: 7 }, (_, i) => 7 - i);   // 7 to 1 (reversed for top-down visual)

  // Strongly Typed Reactive Form
  readonly form: FormGroup<LoadForm> = this.fb.group({
    sku: this.fb.nonNullable.control('', [Validators.required]),
    name: this.fb.nonNullable.control(''),
    weight: this.fb.control<number | null>(null, [Validators.required, Validators.min(1)]),
    isImo: this.fb.nonNullable.control(false)
  });

  // Helpers to get form control errors dynamically
  get skuError(): string {
    const control = this.form.controls.sku;
    return getErrorMessage('sku', control.errors);
  }

  get weightError(): string {
    const control = this.form.controls.weight;
    return getErrorMessage('weight', control.errors);
  }

  ngOnInit(): void {
    this.loadState();
  }

  loadState(): void {
    this.isLoading.set(true);

    this.warehouseService.getWarehouseState()
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.isLoading.set(false))
      )
      .subscribe({
        next: (slots) => {
          this.slots.set(slots);
          
          // Keep selection details updated if same slot ID exists
          const currentSelected = this.selectedSlot();
          if (currentSelected) {
            const updated = slots.find(s => s.id === currentSelected.id);
            this.selectedSlot.set(updated || null);
          }
        },
        error: () => {
          this.showToast('Erro ao carregar o estado do armazém.', 'fechar');
        }
      });

    this.warehouseService.getOccupancyStats()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (stats) => {
          this.stats.set(stats);
        }
      });

    this.warehouseService.getSettings()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (settings) => {
          this.activeHeightRule.set(settings.height_rule);
        }
      });
  }

  getSlot(aisle: number, col: number, level: number): Slot | undefined {
    return this.slots().find(s => s.aisle === aisle && s.column === col && s.level === level);
  }

  selectSlot(slot: Slot): void {
    this.selectedSlot.set(slot);
  }

  requestSuggestion(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.showToast('Por favor, preencha os campos obrigatórios corretamente.', 'OK');
      return;
    }

    const formVal = this.form.getRawValue();
    this.isLoading.set(true);

    const payload = {
      sku: formVal.sku,
      weight: formVal.weight as number,
      is_imo: formVal.isImo
    };

    this.warehouseService.suggestAllocation(payload)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.isLoading.set(false))
      )
      .subscribe({
        next: (res) => {
          const matchingSlot = this.slots().find(s => s.id === res.slot_id) || null;
          this.suggestedSlot.set(matchingSlot);
          this.suggestedMessage.set(res.message);
          
          // Disable form during review/confirmation using Form API, not [disabled] attribute
          this.form.disable();
          this.showToast('Sugestão gerada pela IA!', 'fechar');
        },
        error: (err) => {
          const msg = err.error?.detail || 'Erro ao calcular a melhor posição.';
          this.showToast(msg, 'fechar');
          this.suggestedSlot.set(null);
          this.suggestedMessage.set(null);
        }
      });
  }

  confirmAllocation(): void {
    const activeSuggested = this.suggestedSlot();
    if (!activeSuggested) return;

    const formVal = this.form.getRawValue();
    this.isLoading.set(true);

    const payload = {
      slot_id: activeSuggested.id,
      sku: formVal.sku,
      name: formVal.name || `Carga ${formVal.sku}`,
      weight: formVal.weight || 0,
      is_imo: formVal.isImo
    };

    this.warehouseService.confirmAllocation(payload)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.isLoading.set(false))
      )
      .subscribe({
        next: () => {
          this.showToast('Carga alocada com sucesso!', 'fechar');
          this.clearForm();
          this.loadState();
        },
        error: (err) => {
          const msg = err.error?.detail || 'Erro ao confirmar alocação.';
          this.showToast(msg, 'fechar');
        }
      });
  }

  unloadSlot(slot: Slot): void {
    this.isLoading.set(true);
    this.warehouseService.unloadSlot(slot.id)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.isLoading.set(false))
      )
      .subscribe({
        next: () => {
          this.showToast('Carga removida com sucesso!', 'fechar');
          this.loadState();
        },
        error: (err) => {
          const msg = err.error?.detail || 'Erro ao liberar posição.';
          this.showToast(msg, 'fechar');
        }
      });
  }

  resetWarehouse(): void {
    if (confirm('Tem certeza que deseja esvaziar todo o armazém? Esta ação não pode ser desfeita.')) {
      this.isLoading.set(true);
      this.warehouseService.resetWarehouse()
        .pipe(
          takeUntilDestroyed(this.destroyRef),
          finalize(() => this.isLoading.set(false))
        )
        .subscribe({
          next: () => {
            this.showToast('Armazém reinicializado!', 'fechar');
            this.clearForm();
            this.loadState();
          },
          error: () => {
            this.showToast('Erro ao reiniciar armazém.', 'fechar');
          }
        });
    }
  }

  cancelSuggestion(): void {
    this.suggestedSlot.set(null);
    this.suggestedMessage.set(null);
    this.form.enable();
  }

  clearForm(): void {
    this.form.reset({
      sku: '',
      name: '',
      weight: null,
      isImo: false
    });
    this.form.enable();
    this.suggestedSlot.set(null);
    this.suggestedMessage.set(null);
  }

  onHeightRuleChange(value: string): void {
    this.isLoading.set(true);
    this.warehouseService.updateSettings(value)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.isLoading.set(false))
      )
      .subscribe({
        next: (settings) => {
          this.activeHeightRule.set(settings.height_rule);
          this.showToast('Regra de altura atualizada!', 'fechar');
          this.loadState();
        },
        error: () => {
          this.showToast('Erro ao atualizar regra de altura.', 'fechar');
        }
      });
  }

  private showToast(message: string, action: string): void {
    this.snackBar.open(message, action, {
      duration: 4000,
      horizontalPosition: 'end',
      verticalPosition: 'bottom'
    });
  }
}
