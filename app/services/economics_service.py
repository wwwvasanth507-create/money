from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.payment import DepositRequest, WithdrawalRequest, DepositStatus, WithdrawalStatus
from app.models.game import Game, GameSession, GameCode, SessionStatus
from app.models.user import User, UserRole
from app.models.wallet import WalletTransaction, TransactionType, TransactionStatus
from app.schemas.economics import EconomicsPreviewResponse, GameRTPStat

class EconomicsService:
    @staticmethod
    def get_economics_preview(db: Session) -> EconomicsPreviewResponse:
        # Total Approved Deposits (Wallet Ledger + Deposit Requests)
        wallet_deposits = db.query(func.coalesce(func.sum(WalletTransaction.amount), 0)).filter(
            WalletTransaction.type == "DEPOSIT"
        ).scalar() or 0

        req_deposits = db.query(func.coalesce(func.sum(DepositRequest.amount), 0)).filter(
            DepositRequest.status == "APPROVED"
        ).scalar() or 0

        total_deposits_paise = int(max(wallet_deposits, req_deposits))

        # Total Approved Withdrawals (Wallet Ledger + Withdrawal Requests)
        wallet_withdrawals = db.query(func.coalesce(func.sum(WalletTransaction.amount), 0)).filter(
            WalletTransaction.type.in_(["WITHDRAWAL_PAYOUT", "WITHDRAWAL_LOCK"])
        ).scalar() or 0

        req_withdrawals = db.query(func.coalesce(func.sum(WithdrawalRequest.amount), 0)).filter(
            WithdrawalRequest.status == "APPROVED"
        ).scalar() or 0

        total_withdrawals_paise = int(max(wallet_withdrawals, req_withdrawals))

        # Total Bets across all games (Aviator, Mines, Dice via Wallet Ledger & GameSession)
        wallet_bets_paise = db.query(func.coalesce(func.sum(WalletTransaction.amount), 0)).filter(
            WalletTransaction.type == "BET_PLACED"
        ).scalar() or 0

        session_bets_paise = db.query(func.coalesce(func.sum(GameSession.bet_amount), 0)).filter(
            GameSession.status.in_(["CASHOUT", "BUST"])
        ).scalar() or 0

        total_bets_paise = int(max(wallet_bets_paise, session_bets_paise))

        # Total Payouts across all games
        wallet_payouts_paise = db.query(func.coalesce(func.sum(WalletTransaction.amount), 0)).filter(
            WalletTransaction.type == "BET_WIN"
        ).scalar() or 0

        session_payouts_paise = db.query(func.coalesce(func.sum(GameSession.payout_amount), 0)).filter(
            GameSession.status.in_(["CASHOUT", "BUST"])
        ).scalar() or 0

        total_payouts_paise = int(max(wallet_payouts_paise, session_payouts_paise))

        ggr_paise = total_bets_paise - total_payouts_paise
        ngr_paise = ggr_paise # Net revenue

        # Player counts
        total_players_count = db.query(User).filter(User.role == "PLAYER").count()
        active_players_count = db.query(User).filter(User.role == "PLAYER", User.is_active == True).count()

        # Pending queues
        pending_deposits_count = db.query(DepositRequest).filter(DepositRequest.status == "PENDING").count()
        pending_withdrawals_count = db.query(WithdrawalRequest).filter(WithdrawalRequest.status == "PENDING").count()

        # Game specific stats
        games = db.query(Game).all()
        game_stats = []
        for g in games:
            if g.code == "CRASH":
                g_bets = db.query(func.coalesce(func.sum(WalletTransaction.amount), 0)).filter(
                    WalletTransaction.type == "BET_PLACED",
                    WalletTransaction.description.like("%Aviator%") | (WalletTransaction.reference_type == "AVIATOR_ROUND")
                ).scalar() or 0

                g_payouts = db.query(func.coalesce(func.sum(WalletTransaction.amount), 0)).filter(
                    WalletTransaction.type == "BET_WIN",
                    WalletTransaction.description.like("%Aviator%") | (WalletTransaction.reference_type == "AVIATOR_ROUND")
                ).scalar() or 0

                if g_bets == 0:
                    g_bets = db.query(func.coalesce(func.sum(GameSession.bet_amount), 0)).filter(
                        GameSession.game_id == g.id,
                        GameSession.status.in_(["CASHOUT", "BUST"])
                    ).scalar() or 0
                    g_payouts = db.query(func.coalesce(func.sum(GameSession.payout_amount), 0)).filter(
                        GameSession.game_id == g.id,
                        GameSession.status.in_(["CASHOUT", "BUST"])
                    ).scalar() or 0
            else:
                g_bets = db.query(func.coalesce(func.sum(GameSession.bet_amount), 0)).filter(
                    GameSession.game_id == g.id,
                    GameSession.status.in_(["CASHOUT", "BUST"])
                ).scalar() or 0

                g_payouts = db.query(func.coalesce(func.sum(GameSession.payout_amount), 0)).filter(
                    GameSession.game_id == g.id,
                    GameSession.status.in_(["CASHOUT", "BUST"])
                ).scalar() or 0

            g_bets = int(g_bets)
            g_payouts = int(g_payouts)
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


