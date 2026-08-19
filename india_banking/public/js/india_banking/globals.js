import BankLogoCard from "./components/BankLogoCard.vue";
import AvailableBanks from "./components/AvailableBanks.vue";
import ConnectedBankList from "./components/ConnectedBankList.vue";
import ConnectedBankCard from "./components/ConnectedBankCard.vue";
import AddBankCard from "./components/AddBankCard.vue";
import SkeletonCard from "./components/SkeletonCard.vue";

export function registerGlobalComponents(app) {
	app.component("BankLogoCard", BankLogoCard);
	app.component("AvailableBanks", AvailableBanks);
	app.component("ConnectedBankList", ConnectedBankList);
	app.component("ConnectedBankCard", ConnectedBankCard);
	app.component("SkeletonCard", SkeletonCard);
	app.component("AddBankCard", AddBankCard);
}
