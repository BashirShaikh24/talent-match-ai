import {
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input,
  Output,
  ViewEncapsulation,
} from '@angular/core';
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
  ) {}

  ringStyle(percentage: number) {
    const color = this.scoreColor(percentage);
    const deg = (percentage / 100) * 360;

    return {
      background: `conic-gradient(${color} ${deg}deg, var(--border) ${deg}deg)`,
    };
  }

  scoreColor(percentage: number): string {
    if (percentage >= 75) return 'var(--mint)';
    if (percentage >= 50) return 'var(--amber)';

    return 'var(--coral)';
  }

  scoreLabel(percentage: number): string {
    if (percentage >= 75) return 'Strong match';
    if (percentage >= 50) return 'Partial match';

    return 'Weak match';
  }

  evaluateFit() {
    this.isMatching = true;

    this.talentMatchService
      .getMatchScore(this.candidate, this.uploadedJdResult)
      .pipe(
        map((matchResult: CandidateData) => ({ matchResult, error: null })),
        catchError((err) => of({ matchResult: null, error: err })),
      )
      .subscribe(({ matchResult, error }) => {
        this.isMatching = false;

        if (error || !matchResult) {
          this.toastr.error(
            `Failed to evaluate fit for ${this.candidate?.name}. Please try again.`,
          );
          return;
        }

        this.candidate = {
          ...this.candidate,
          match_percentage: matchResult.match_percentage,
        };

        this.cdr.markForCheck();
        this.toastr.success(
          `${this.candidate.name} evaluated — ${matchResult.match_percentage}% match.`,
        );
      });
  }

  downloadResume(fileName: string) {
    this.talentMatchService.downloadUploadedFile(fileName, UploadType.CD).subscribe((blob) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');

      a.href = url;
      a.download = fileName;
      a.click();
      window.URL.revokeObjectURL(url);
    });
  }

  closeDetailsModal() {
    this.talentMatchService.isModalOpen.set({ state: false, selectedData: null, uploadedType: '' });
  }
}
