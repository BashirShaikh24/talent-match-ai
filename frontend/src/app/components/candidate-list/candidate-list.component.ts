import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  EventEmitter,
  Input,
  Output,
  ViewEncapsulation,
} from '@angular/core';
import { SlicePipe } from '@angular/common';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ToastrService } from 'ngx-toastr';
import { CandidateData, UploadType } from '../../models';
import { SkeletonPlaceholderComponent } from './skeleton-placeholder';
import { TalentMatchService } from '../../services';

@Component({
  selector: 'app-candidate-list',
  templateUrl: './candidate-list.component.html',
  styleUrl: './candidate-list.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  encapsulation: ViewEncapsulation.None,
  imports: [SlicePipe, SkeletonPlaceholderComponent],
})
export class CandidateListComponent {
  @Input() candidates: CandidateData[] = [];
  @Input() isJdUploaded = false;
  @Input() isMatching = false;

  @Output() getCandidateMatchScores = new EventEmitter<boolean>();

  constructor(
    private talentMatchService: TalentMatchService,
    private destroyRef: DestroyRef,
    private toastr: ToastrService,
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

  // Emit a signal to start the overall candidate evaluation process.
  fetchCandidateMatchScores(): void {
    this.getCandidateMatchScores.emit(true);
  }

  // Download the uploaded candidate resume as a file.
  downloadResume(fileName: string): void {
    this.talentMatchService
      .downloadUploadedFile(fileName, UploadType.CD)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (blob) => {
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');

          a.href = url;
          a.download = this.talentMatchService.removeTimestampFromFilename(fileName);
          a.click();
          window.URL.revokeObjectURL(url);
        },
        error: (err) => {
          console.error('Download failed:', err);
          this.toastr.error('Failed to download the resume. Please try again.');
        },
      });
  }

  // Open the details modal for the selected candidate.
  openDetails(candidate: CandidateData): void {
    this.talentMatchService.isModalOpen.set({
      state: true,
      selectedData: candidate,
      uploadedType: UploadType.CD,
    });
  }
}
