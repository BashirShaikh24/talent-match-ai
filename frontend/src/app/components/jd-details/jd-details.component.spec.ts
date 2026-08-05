import { ComponentFixture, TestBed } from '@angular/core/testing';
import { JdDetailsComponent } from './jd-details.component';

describe('JdDetailsComponent', () => {
  let component: JdDetailsComponent;
  let fixture: ComponentFixture<JdDetailsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [JdDetailsComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(JdDetailsComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
