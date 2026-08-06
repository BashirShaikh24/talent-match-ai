import {
  ChangeDetectorRef,
  Component,
  DestroyRef,
  EventEmitter,
  Input,
  Output,
  ViewEncapsulation,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CandidateData, JobDescriptionData, UploadType } from '../../models';
import { catchError, map, of } from 'rxjs';
import { ToastrService } from 'ngx-toastr';
import { TalentMatchService } from '../../services';

@Component({
  selector: 'app-cd-details',
  templateUrl: './cd-details.component.html',
  styleUrl: './cd-details.component.scss',
  encapsulation: ViewEncapsulation.None,
})
export class CdDetailsComponent {
  @Input() candidate: CandidateData | null = null;
  @Input() uploadedJdResult: JobDescriptionData | null = null;
  @Output() closeModal = new EventEmitter<boolean>();

  isMatching = false;

  constructor(
    public talentMatchService: TalentMatchService,
    private toastr: ToastrService,
    private cdr: ChangeDetectorRef,
    private destroyRef: DestroyRef,
  ) {}

  // Build the circular score styling based on the match percentage.
  ringStyle(percentage: number): { background: string } {
    const color = this.scoreColor(percentage);
    const deg = (percentage / 100) * 360;

    return {
      background: `conic-gradient(${color} ${deg}deg, var(--border) ${deg}deg)`,
    };
  }

  public scoreColor(percentage: number): string {
    if (percentage >= 75) return 'var(--mint)';
    if (percentage >= 50) return 'var(--amber)';

    return 'var(--coral)';
  }

  public scoreLabel(percentage: number): string {
    if (percentage >= 75) return 'Strong match';
    if (percentage >= 50) return 'Partial match';

    return 'Weak match';
  }

  // Evaluate the currently selected candidate against the uploaded job description.
  evaluateFit(): void {
    if (!this.candidate) {
      return;
    }

    this.isMatching = true;
    this.talentMatchService.isCandidateEvaluated.set({ ...this.candidate, isMatching: true });

    this.talentMatchService
      .getMatchScore(this.candidate, this.uploadedJdResult)
      .pipe(
        map((matchResult: CandidateData) => ({ matchResult, error: null })),
        catchError((err) => of({ matchResult: null, error: err })),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(({ matchResult, error }) => {
        this.isMatching = false;

        if (error || !matchResult) {
          this.toastr.error(
            `Failed to evaluate fit for ${this.candidate?.name}. Please try again.`,
          );
          this.talentMatchService.isCandidateEvaluated.set({
            ...this.candidate!,
            isMatching: false,
          });
          return;
        }

        this.candidate = {
          ...this.candidate,
          match_percentage: matchResult.match_percentage,
          isMatching: false,
        };

        this.cdr.markForCheck();
        this.toastr.success(
          `${this.candidate.name} evaluated — ${matchResult.match_percentage}% match.`,
        );
        this.talentMatchService.isCandidateEvaluated.set(this.candidate);
      });
  }

  // Download the selected candidate resume file.
  downloadResume(fileName: string): void {
    this.talentMatchService
      .downloadUploadedFile(fileName, UploadType.CD)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (blob) => {
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');

          a.href = url;
          a.download = fileName;
          a.click();
          window.URL.revokeObjectURL(url);
        },
        error: (err) => {
          console.error('Download failed:', err);
          this.toastr.error('Failed to download the resume. Please try again.');
        },
      });
  }

  // Close the modal and reset the selected candidate state.
  closeDetailsModal(): void {
    this.talentMatchService.isModalOpen.set({ state: false, selectedData: null, uploadedType: '' });
  }
}
