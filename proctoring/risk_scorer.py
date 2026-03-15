from config import Config

WEIGHTS = Config.VIOLATION_WEIGHTS
DECAY = 0.97

class RiskScorer:
    def __init__(self):
        self.score = 0.0
        self.violation_counts = {k: 0 for k in WEIGHTS}
        self.total_violations = 0

    def update(self, alerts):
        alerts = list(set(alerts))
        # Base decay if no alerts: slowly recover trust
        if not alerts:
            self.score = max(0.0, self.score - 1.2)
            
        for vtype, msg, severity in alerts:
            if vtype in WEIGHTS:
                # Direct strict addition of the configured weight
                weight = WEIGHTS[vtype] * 0.6
                self.score += weight
                self.violation_counts[vtype] = self.violation_counts.get(vtype, 0) + 1
                self.total_violations += 1

        self.score = max(0.0, min(100.0, self.score))
        return round(self.score, 1)

    def get_risk_level(self):
        if self.score < Config.RISK_LOW:
            return 'low', '#28a745'
        elif self.score < Config.RISK_MEDIUM:
            return 'medium', '#ffc107'
        elif self.score < Config.RISK_HIGH:
            return 'high', '#fd7e14'
        else:
            return 'critical', '#dc3545'

    def get_summary(self):
        level, color = self.get_risk_level()
        return {
            'score': round(self.score, 1),
            'level': level,
            'color': color,
            'total_violations': self.total_violations,
            'violation_counts': self.violation_counts
        }

    def reset(self):
        self.score = 0.0
        self.violation_counts = {k: 0 for k in WEIGHTS}
        self.total_violations = 0