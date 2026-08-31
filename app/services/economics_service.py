from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.payment import DepositRequest, WithdrawalRequest, DepositStatus, WithdrawalStatus
from app.models.game import Game, GameSession, SessionStatus
from app.models.user import User, UserRole
from app.schemas.economics import EconomicsPreviewResponse, GameRTPStat

class EconomicsService:
    @staticmethod
    def get_economics_preview(db: Session) -> EconomicsPreviewResponse:
        # Total Approved Deposits
        total_deposits_paise = db.query(func.coalesce(func.sum(DepositRequest.amount), 0)).filter(
            DepositRequest.status == DepositStatus.APPROVED.value
        ).scalar() or 0

        # Total Approved Withdrawals
        total_withdrawals_paise = db.query(func.coalesce(func.sum(WithdrawalRequest.amount), 0)).filter(
            WithdrawalRequest.status == WithdrawalStatus.APPROVED.value
        ).scalar() or 0

        # Total Bets & Payouts across ended game sessions
        total_bets_paise = db.query(func.coalesce(func.sum(GameSession.bet_amount), 0)).filter(
            GameSession.status.in_([SessionStatus.CASHOUT.value, SessionStatus.BUST.value])
        ).scalar() or 0

        total_payouts_paise = db.query(func.coalesce(func.sum(GameSession.payout_amount), 0)).filter(
            GameSession.status.in_([SessionStatus.CASHOUT.value, SessionStatus.BUST.value])
        ).scalar() or 0

        ggr_paise = total_bets_paise - total_payouts_paise
        ngr_paise = ggr_paise # Net revenue

        # Player counts
        total_players_count = db.query(User).filter(User.role == UserRole.PLAYER.value).count()
        active_players_count = db.query(User).filter(User.role == UserRole.PLAYER.value, User.is_active == True).count()

        # Pending queues
        pending_deposits_count = db.query(DepositRequest).filter(DepositRequest.status == DepositStatus.PENDING.value).count()
        pending_withdrawals_count = db.query(WithdrawalRequest).filter(WithdrawalRequest.status == WithdrawalStatus.PENDING.value).count()

        # Game specific stats
        games = db.query(Game).all()
        game_stats = []
        for g in games:
            g_bets = db.query(func.coalesce(func.sum(GameSession.bet_amount), 0)).filter(
                GameSession.game_id == g.id,
                GameSession.status.in_([SessionStatus.CASHOUT.value, SessionStatus.BUST.value])
            ).scalar() or 0

            g_payouts = db.query(func.coalesce(func.sum(GameSession.payout_amount), 0)).filter(
                GameSession.game_id == g.id,
                GameSession.status.in_([SessionStatus.CASHOUT.value, SessionStatus.BUST.value])
            ).scalar() or 0

            g_ggr = g_bets - g_payouts
            rtp_percent = round((g_payouts / g_bets * 100.0), 2) if g_bets > 0 else 0.0

            game_stats.append(GameRTPStat(
                game_code=g.code,
                game_name=g.name,
                total_bets=g_bets,
                total_bets_inr=g_bets / 100.0,
                total_payouts=g_payouts,
                total_payouts_inr=g_payouts / 100.0,
                ggr=g_ggr,
                ggr_inr=g_ggr / 100.0,
                actual_rtp_percent=rtp_percent
            ))

        return EconomicsPreviewResponse(
            total_deposits_paise=total_deposits_paise,
            total_deposits_inr=total_deposits_paise / 100.0,
            total_withdrawals_paise=total_withdrawals_paise,
            total_withdrawals_inr=total_withdrawals_paise / 100.0,
            total_bets_paise=total_bets_paise,
            total_bets_inr=total_bets_paise / 100.0,
            total_payouts_paise=total_payouts_paise,
            total_payouts_inr=total_payouts_paise / 100.0,
            ggr_paise=ggr_paise,
            ggr_inr=ggr_paise / 100.0,
            ngr_paise=ngr_paise,
            ngr_inr=ngr_paise / 100.0,
            total_players_count=total_players_count,
            active_players_count=active_players_count,
            pending_deposits_count=pending_deposits_count,
            pending_withdrawals_count=pending_withdrawals_count,
            game_stats=game_stats
        )
