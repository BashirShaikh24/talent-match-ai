import {
  ChangeDetectorRef,
  Component,
  DestroyRef,
  effect,
  OnInit,
  ViewEncapsulation,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  HeaderComponent,
  CandidateListComponent,
  FileUploadComponent,
  DetailsModalComponent,
  CdDetailsComponent,
  JdDetailsComponent,
} from './components';
import { CandidateData, CandidateMatchResult, JobDescriptionData, UploadType } from './models';
import { catchError, concatMap, from, map, of } from 'rxjs';
import { ToastrService } from 'ngx-toastr';
import { TalentMatchService } from './services';

@Component({
  selector: 'app-root',
  imports: [
    HeaderComponent,
    CandidateListComponent,
    FileUploadComponent,
    DetailsModalComponent,
    CdDetailsComponent,
    JdDetailsComponent,
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss',
  encapsulation: ViewEncapsulation.None,
})
export class App implements OnInit {
  title = 'talent-match-ai';
  candidates: CandidateData[] = [];
  uploadTypeEnum = UploadType;
  uploadedJdResult: JobDescriptionData | null = null;
  isMatching: boolean = false;

  constructor(
    public talentMatchService: TalentMatchService,
    private cdr: ChangeDetectorRef,
    private destroyRef: DestroyRef,
    private toastr: ToastrService,
  ) {
    // Keep the candidate list in sync whenever a modal evaluation updates the shared signal.
    effect(() => {
      const candidateEvaluated = this.talentMatchService.isCandidateEvaluated();

      if (candidateEvaluated?.filename) {
        this.updateCandidateState(candidateEvaluated.filename, {
          match_percentage: candidateEvaluated.match_percentage,
          isMatching: candidateEvaluated.isMatching ?? false,
        });
      }
    });
  }

  ngOnInit(): void {
    this.getCandidateList();
  }

  // Update a single candidate in the local list state without rebuilding the whole array.
  private updateCandidateState(filename: string | undefined, patch: Partial<CandidateData>) {
    if (!filename) {
      return;
    }

    this.candidates = this.candidates.map((candidate) =>
      candidate.filename === filename ? { ...candidate, ...patch } : candidate,
    );
    this.cdr.markForCheck();
  }

  // Clear the UI-only match scores whenever a new job description is loaded.
  private resetEvaluationState(): void {
    this.isMatching = false;
    this.talentMatchService.isCandidateEvaluated.set(null);

    this.candidates = this.candidates.map((candidate: CandidateData) => ({
      ...candidate,
      match_percentage: null,
      isMatching: false,
    }));

    this.cdr.markForCheck();
  }

  // Load candidates from the backend and hydrate the UI with the server payload only.
  getCandidateList(): void {
    this.talentMatchService
      .getCandidateList()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((data) => {
        const freshCandidates = data as CandidateData[];

        this.candidates = freshCandidates.map((fresh) => ({
          ...fresh,
          isMatching: false,
          match_percentage: fresh.match_percentage ?? null,
        }));

        this.cdr.markForCheck();
      });
  }

  // Refresh the candidate list after a resume or job description upload is processed.
  onFileProcessed(
    response: JobDescriptionData | CandidateData | null,
    uploadType: UploadType,
  ): void {
    if (uploadType === UploadType.JD) {
      this.uploadedJdResult = response as JobDescriptionData;
      this.resetEvaluationState();
    } else {
      this.getCandidateList();
    }
  }

  // Evaluate all candidates that do not yet have a match percentage.
  fetchCandidateMatchScores(response: boolean): void {
    if (!response) {
      return;
    }

    const jdResult = this.uploadedJdResult;

    if (!jdResult) {
      this.toastr.error('Please upload a job description before matching.');

      return;
    }

    this.isMatching = true;

    const toMatch = this.candidates.filter((c) => c.match_percentage == null);

    if (toMatch.length === 0) {
      this.toastr.info('All candidates were already matched.');
      this.isMatching = false;

      return;
    }

    let hasError = false;

    from(toMatch)
      .pipe(
        concatMap((candidate) => {
          this.updateCandidateState(candidate.filename, { isMatching: true });

          return this.talentMatchService.getMatchScore(candidate, jdResult).pipe(
            map((matchResult: CandidateMatchResult) => ({ candidate, matchResult, error: null })),
            catchError((err) => of({ candidate, matchResult: null, error: err })),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: ({ candidate, matchResult, error }) => {
          if (error) {
            hasError = true;
          }

          this.updateCandidateState(candidate.filename, {
            match_percentage: matchResult
              ? matchResult.match_percentage
              : candidate.match_percentage,
            isMatching: false,
          });
        },
        complete: () => {
          this.isMatching = false;
          if (hasError) {
            this.toastr.warning('Matching complete, but some candidates failed.');
          } else {
            this.toastr.success('Matching complete! Candidates ranked by best fit.');
          }
        },
      });
  }
}
