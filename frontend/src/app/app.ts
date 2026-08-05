import { ChangeDetectorRef, Component, OnInit, ViewEncapsulation } from '@angular/core';
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
  selectedCandidate: CandidateData | null = null;

  constructor(
    public talentMatchService: TalentMatchService,
    private cdr: ChangeDetectorRef,
    private toastr: ToastrService,
  ) {}

  ngOnInit(): void {
    this.getCandidateList();
  }

  getCandidateList() {
    this.talentMatchService.getCandidateList().subscribe((data) => {
      const freshCandidates = data as CandidateData[];

      this.candidates = freshCandidates.map((fresh) => {
        const existing = this.candidates.find((c) => c.filename === fresh.filename);

        if (existing?.match_percentage != null) {
          return { ...fresh, match_percentage: existing.match_percentage };
        }

        return fresh;
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
          this.candidates = this.candidates.map((c) =>
            c.filename === candidate.filename ? { ...c, isMatching: true } : c,
          );
          this.cdr.markForCheck();

          return this.talentMatchService.getMatchScore(candidate, this.uploadedJdResult).pipe(
            map((matchResult: CandidateData) => ({ candidate, matchResult, error: null })),
            catchError((err) => of({ candidate, matchResult: null, error: err })),
          );
        }),
      )
      .subscribe({
        next: ({ candidate, matchResult, error }) => {
          if (error) {
            hasError = true;
            this.isMatching = false;
          }

          this.candidates = this.candidates.map((c) =>
            c.filename === candidate.filename
              ? {
                  ...c,
                  match_percentage: matchResult ? matchResult.match_percentage : c.match_percentage,
                  isMatching: false,
                }
              : c,
          );
          this.cdr.markForCheck();
        },
        complete: () => {
          this.isMatching = false;
          hasError
            ? this.toastr.warning('Matching complete, but some candidates failed.')
            : this.toastr.success('Matching complete! Candidates ranked by best fit.');
        },
      });
  }

  openDetails(candidate: CandidateData) {
    this.selectedCandidate = candidate;
  }

  closeDetails() {
    this.selectedCandidate = null;
  }
}
