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
import { CandidateData, JobDescriptionData, UploadType } from './models';
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

  private updateCandidateState(filename: string | undefined, patch: Partial<CandidateData>) {
    if (!filename) {
      return;
    }

    this.candidates = this.candidates.map((candidate) =>
      candidate.filename === filename ? { ...candidate, ...patch } : candidate,
    );
    this.cdr.markForCheck();
  }

  getCandidateList() {
    this.talentMatchService
      .getCandidateList()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((data) => {
        const freshCandidates = data as CandidateData[];

        this.candidates = freshCandidates.map((fresh) => {
          const existing = this.candidates.find(
            (candidate) => candidate.filename === fresh.filename,
          );

          if (existing?.match_percentage != null) {
            return {
              ...fresh,
              match_percentage: existing.match_percentage,
              isMatching: false,
            };
          }

          return { ...fresh, isMatching: false };
        });

        this.cdr.markForCheck();
      });
  }

  onFileProcessed(response: JobDescriptionData | CandidateData | null, uploadType: UploadType) {
    if (uploadType === UploadType.JD) {
      this.uploadedJdResult = response as JobDescriptionData;
    }
    this.getCandidateList();
  }

  fetchCandidateMatchScores(response: boolean) {
    if (!response) {
      return;
    }

    this.isMatching = true;

    const toMatch = this.candidates.filter((c) => c.match_percentage == null);

    if (toMatch.length === 0) {
      this.toastr.info('All candidates were already matched.');

      return;
    }

    let hasError = false;

    from(toMatch)
      .pipe(
        concatMap((candidate) => {
          this.updateCandidateState(candidate.filename, { isMatching: true });

          return this.talentMatchService.getMatchScore(candidate, this.uploadedJdResult).pipe(
            map((matchResult: CandidateData) => ({ candidate, matchResult, error: null })),
            catchError((err) => of({ candidate, matchResult: null, error: err })),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: ({ candidate, matchResult, error }) => {
          if (error) {
            hasError = true;
            this.isMatching = false;
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
          hasError
            ? this.toastr.warning('Matching complete, but some candidates failed.')
            : this.toastr.success('Matching complete! Candidates ranked by best fit.');
        },
      });
  }
}
